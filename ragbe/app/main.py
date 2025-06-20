from fastapi import FastAPI, Request
from pydantic import BaseModel
from rag import query_rag
from ingest import ingest_documents

app = FastAPI()

class Question(BaseModel):
    text: str

@app.post("/ask")
async def ask(q: Question):
    return query_rag(q.text)

@app.post("/ingest")
async def ingest():
    return ingest_documents("./docs")
