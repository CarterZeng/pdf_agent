import os
import re
import shutil
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document


# --- Embedding Wrapper ---
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(["passage: " + t for t in texts], normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode(["query: " + text], normalize_embeddings=True)[0].tolist()


# --- RAG Core Logic ---
class PdfRAGAgent:
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5", temperature: float = 0, pdfs_folder: str = "./pdfs"):
        self.pdfs_folder = pdfs_folder
        self.abstract_path = "faiss_abstract"
        self.fulltext_path = "faiss_full"
        self.embeddings = SentenceTransformerEmbeddings(model_name)
        self.llm = ChatOpenAI(
            model="openai/gpt-oss-120b",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("LEO_API_KEY"),
            temperature=temperature
        )
        self.chat_history = []

    def extract_abstract(self, text: str) -> str | None:
        pattern = r"Abstract(.*?)(Introduction|1\.|I\.)"
        match = re.search(pattern, text, re.S | re.I)
        return match.group(1).strip() if match else None

    def build_vector_store_from_pdfs(self):
        for path in [self.abstract_path, self.fulltext_path]:
            if os.path.exists(path):
                shutil.rmtree(path)

        if not os.path.exists(self.pdfs_folder):
            os.makedirs(self.pdfs_folder)

        pdf_files = [f for f in os.listdir(self.pdfs_folder) if f.endswith(".pdf")]
        all_abstract_docs = []
        all_full_chunks = []
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

        for file in pdf_files:
            path = os.path.join(self.pdfs_folder, file)
            reader = PdfReader(path)

            cover_text = "\n".join([p.extract_text() or "" for p in reader.pages[:2]])
            abstract = self.extract_abstract(cover_text)
            if abstract:
                all_abstract_docs.append(Document(page_content=abstract, metadata={"source": file, "page": 1}))

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    chunks = splitter.split_text(page_text)
                    for chunk in chunks:
                        all_full_chunks.append(Document(page_content=chunk, metadata={"source": file, "page": i + 1}))

        if all_abstract_docs:
            FAISS.from_documents(all_abstract_docs, self.embeddings).save_local(self.abstract_path)
        if all_full_chunks:
            FAISS.from_documents(all_full_chunks, self.embeddings).save_local(self.fulltext_path)

    def answer(self, query: str) -> Dict[str, Any]:
        try:
            abs_store = FAISS.load_local(self.abstract_path, self.embeddings, allow_dangerous_deserialization=True)
            full_store = FAISS.load_local(self.fulltext_path, self.embeddings, allow_dangerous_deserialization=True)
        except Exception:
            raise HTTPException(status_code=404, detail="Index not found. Please run /reindex.")

        abs_results = abs_store.similarity_search(query, k=2)
        candidates = list(set(d.metadata.get("source") for d in abs_results))

        def filter_fn(meta):
            return meta.get("source") in candidates

        docs = full_store.similarity_search(query, k=5, filter=filter_fn if candidates else None)

        rag_results = []
        context_list = []
        for i, d in enumerate(docs):
            src = d.metadata.get("source", "Unknown")
            pg = d.metadata.get("page", "N/A")
            context_list.append(f"[Ref {i + 1} | {src} P.{pg}]\n{d.page_content}")
            rag_results.append({
                "ref_id": i + 1,
                "source": src,
                "page": pg,
                "content": d.page_content.strip()
            })

        history_context = "\n".join(self.chat_history)
        system_prompt = f"""Academic Assistant. Answer based ONLY on context. Cite [1], [2].

        [HISTORY]
        {history_context}

        [CONTEXT]
        {"\n\n".join(context_list)}
        """

        response = self.llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=query)])

        # Update history as strings for the response
        self.chat_history.append(f"User: {query}")
        self.chat_history.append(f"Assistant: {response.content}")

        if len(self.chat_history) > 10:
            self.chat_history = self.chat_history[-10:]

        return {
            "response": response.content,
            "RAG_RESULT": rag_results,
            "chat_history": self.chat_history
        }


# --- FastAPI ---
app = FastAPI(title="Academic RAG API")
agent = PdfRAGAgent()


class QueryRequest(BaseModel):
    prompt: str


@app.on_event("startup")
async def startup_event():
    if not os.path.exists("faiss_full"):
        agent.build_vector_store_from_pdfs()


@app.post("/chat")
async def chat(request: QueryRequest):
    return agent.answer(request.prompt)


@app.post("/reindex")
async def reindex():
    agent.build_vector_store_from_pdfs()
    return {"message": "Success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)