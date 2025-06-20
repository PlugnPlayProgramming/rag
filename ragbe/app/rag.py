from qdrant_client import QdrantClient
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
import requests, json, re, os

base_url       = os.getenv("LLM_URL"        , "http://ollama:11434/api/generate")
api_key        = os.getenv("LLM_API_KEY"    , "not-needed")
llm_model_name = os.getenv("LLM_MODEL_NAME" , "deepseek-r1:8b")
emb_model_name = os.getenv("EMB_MODEL_NAME" , "bge-base-en")
collection_name= os.getenv("COLLECTION_NAME", "rag_docs")

qdrant = QdrantClient(host="qdrant", port=6333, https=False)
existing_collections = [col.name for col in qdrant.get_collections().collections]

if collection_name not in existing_collections:
    qdrant.recreate_collection(
        collection_name=collection_name,
        vectors_config={"size": 768, "distance": "Cosine"}  # BGE 모델 기준
    )

embedding = HuggingFaceEmbeddings(
    model_name=f"/models/{emb_model_name}",
    model_kwargs={"trust_remote_code": True}
)

doc_store = QdrantVectorStore(
    client=qdrant,
    collection_name=collection_name,
    embedding=embedding,
)

def query_rag(query_text: str):
    docs = doc_store.similarity_search(query_text, k=3)
    context = "\n".join([d.page_content for d in docs])
    prompt = (
        f"Based on the following documents, answer the question. "
        f"Documents:\n\n{context}\n\nQuestion: {query_text}"
    )

    try:
        res = requests.post(
            base_url,
            json={"model": llm_model_name, "prompt": prompt},
            stream=True,
            timeout=60,
        )
        res.raise_for_status()

        output = ""
        for line in res.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    output += data.get("response", "")
                except json.JSONDecodeError:
                    continue
                
        # remove <think>...</think> block if it exists
        #output = re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL)
        
        # 1) <think> … </think> 완전쌍 제거
        output = re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL | re.IGNORECASE)
        # 2) 짝이 없는 </think>가 있을 때 → 처음부터 </think>까지 몽땅 삭제
        output = re.sub(r"^.*?</think>", "", output, flags=re.DOTALL | re.IGNORECASE)
        # 3) 혹시 남아 있을 고립된 <think> / </think> 태그도 삭제
        output = re.sub(r"</?think>", "", output, flags=re.IGNORECASE)        
        # 4) 혹시 남아 있을 고립된 <end_of_turn> / </end_of_turn> 태그도 삭제
        output = re.sub(r"</?end_of_turn>", "", output, flags=re.IGNORECASE)
                
        return {"response": output.strip() or "No response"}
    except Exception as e:
        return {"response": f"Error: {e}"}
