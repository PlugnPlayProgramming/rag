from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredFileLoader
from rag import doc_store

def ingest_documents(doc_dir: str):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    all_docs = []
    from pathlib import Path
    for path in Path(doc_dir).glob("*.docx"):
        loader = UnstructuredFileLoader(str(path))
        docs = loader.load()
        chunks = splitter.split_documents(docs)
        all_docs.extend(chunks)

    doc_store.add_documents(all_docs)
    return {"status": "done", "count": len(all_docs)}
