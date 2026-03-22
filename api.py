import os
import re
import shutil
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 数据模型 ---
class QueryRequest(BaseModel):
    prompt: str


# --- Embedding Wrapper ---
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"✓ Embedding model '{model_name}' loaded successfully")
        except Exception as e:
            logger.error(f"✗ Failed to load embedding model: {e}")
            raise

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
        
        try:
            self.embeddings = SentenceTransformerEmbeddings(model_name)
            self.llm = ChatOpenAI(
                model="openai/gpt-oss-120b",
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("LEO_API_KEY"),
                temperature=temperature
            )
            logger.info("✓ PdfRAGAgent initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to initialize PdfRAGAgent: {e}")
            raise
            
        self.chat_history = []

    def extract_abstract(self, text: str) -> str | None:
        pattern = r"Abstract(.*?)(Introduction|1\.|I\.)"
        match = re.search(pattern, text, re.S | re.I)
        return match.group(1).strip() if match else None

    def build_vector_store_from_pdfs(self):
        """Build vector stores from PDFs in the folder"""
        try:
            # Clean old indexes
            for path in [self.abstract_path, self.fulltext_path]:
                if os.path.exists(path):
                    shutil.rmtree(path)
                    logger.info(f"✓ Cleaned old index: {path}")

            if not os.path.exists(self.pdfs_folder):
                os.makedirs(self.pdfs_folder)
                logger.warning(f"⚠ Created PDFs folder: {self.pdfs_folder}")

            pdf_files = [f for f in os.listdir(self.pdfs_folder) if f.endswith(".pdf")]
            if not pdf_files:
                logger.warning("⚠ No PDF files found in folder")
                return

            all_abstract_docs = []
            all_full_chunks = []
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

            for file in pdf_files:
                try:
                    path = os.path.join(self.pdfs_folder, file)
                    logger.info(f"Processing: {file}")
                    
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
                    
                    logger.info(f"✓ Successfully processed: {file}")
                except Exception as e:
                    logger.error(f"✗ Error processing {file}: {e}")
                    continue

            # Build indexes
            if all_abstract_docs:
                FAISS.from_documents(all_abstract_docs, self.embeddings).save_local(self.abstract_path)
                logger.info(f"✓ Abstract index built with {len(all_abstract_docs)} documents")
            
            if all_full_chunks:
                FAISS.from_documents(all_full_chunks, self.embeddings).save_local(self.fulltext_path)
                logger.info(f"✓ Full-text index built with {len(all_full_chunks)} chunks")
                
        except Exception as e:
            logger.error(f"✗ Error building vector stores: {e}")
            raise

    def answer(self, query: str) -> Dict[str, Any]:
        """Generate answer based on query using RAG"""
        try:
            # Load vector stores
            try:
                abs_store = FAISS.load_local(self.abstract_path, self.embeddings, allow_dangerous_deserialization=True)
                full_store = FAISS.load_local(self.fulltext_path, self.embeddings, allow_dangerous_deserialization=True)
            except Exception:
                logger.error("Vector stores not found. Please run /reindex.")
                raise HTTPException(status_code=404, detail="Index not found. Please run POST /reindex")

            # Hierarchical retrieval: Abstract -> Full text
            abs_results = abs_store.similarity_search(query, k=2)
            candidates = list(set(d.metadata.get("source") for d in abs_results))
            logger.info(f"Found {len(candidates)} candidate documents")

            # Filter full-text results manually (FAISS doesn't support filter parameter)
            all_full_results = full_store.similarity_search(query, k=10)
            
            if candidates:
                docs = [d for d in all_full_results if d.metadata.get("source") in candidates][:5]
            else:
                docs = all_full_results[:5]

            if not docs:
                logger.warning("No relevant documents found")
                return {
                    "response": "I'm sorry, but no relevant information was found in the provided documents.",
                    "rag_results": [],
                    "RAG_RESULT": [],
                    "chat_history": self.chat_history,
                    "status": "success"
                }

            # Prepare RAG context
            rag_results = []
            context_list = []
            
            for i, d in enumerate(docs):
                src = d.metadata.get("source", "Unknown")
                pg = d.metadata.get("page", "N/A")
                ref_id = i + 1
                
                context_list.append(f"[Ref {ref_id} | {src} P.{pg}]\n{d.page_content}")
                rag_results.append({
                    "ref_id": ref_id,
                    "source": src,
                    "page": pg,
                    "content": d.page_content.strip()
                })

            # Construct system prompt
            history_context = ""
            if self.chat_history:
                history_context = "\n".join(self.chat_history[-4:])

            system_prompt = f"""You are an academic research assistant. 
Answer based ONLY on the provided context. 
Always cite references like [1], [2] when referencing specific information.
If the context doesn't contain the answer, say so clearly.

{f'[CONVERSATION HISTORY]{chr(10)}{history_context}{chr(10)}{chr(10)}' if history_context else ''}[CONTEXT]
{chr(10).join(context_list)}
"""

            # Call LLM
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ])

            answer_text = response.content
            
            # Update chat history
            self.chat_history.append(f"User: {query}")
            self.chat_history.append(f"Assistant: {answer_text}")
            
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]

            logger.info(f"✓ Generated answer (history length: {len(self.chat_history)})")

            return {
                "response": answer_text,
                "rag_results": rag_results,
                "RAG_RESULT": rag_results,  # 兼容两种字段名
                "chat_history": self.chat_history,
                "status": "success"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"✗ Error in answer generation: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# --- FastAPI App Setup ---
app = FastAPI(
    title="PDF Agent RAG API",
    description="Academic RAG system with LLM integration",
    version="1.0.0"
)

# ✅ CORS middleware - 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
try:
    agent = PdfRAGAgent()
    logger.info("✓ Agent initialized")
except Exception as e:
    logger.error(f"✗ Failed to initialize agent: {e}")
    raise


@app.on_event("startup")
async def startup_event():
    """Initialize vector stores on startup"""
    try:
        if not os.path.exists(agent.fulltext_path):
            logger.info("Building vector stores...")
            agent.build_vector_store_from_pdfs()
        else:
            logger.info("✓ Vector stores already exist")
    except Exception as e:
        logger.error(f"⚠ Error during startup: {e}")


# ✅ 健康检查端点
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "abstract_index": os.path.exists(agent.abstract_path),
        "fulltext_index": os.path.exists(agent.fulltext_path)
    }


# ✅ 聊天端点
@app.post("/chat")
async def chat(request: QueryRequest):
    """Chat endpoint with RAG"""
    logger.info(f"Query received: {request.prompt[:50]}...")
    return agent.answer(request.prompt)


# ✅ 重新索引端点
@app.post("/reindex")
async def reindex():
    """Rebuild vector stores"""
    try:
        logger.info("Starting reindexing...")
        agent.build_vector_store_from_pdfs()
        return {"status": "success", "message": "Vector stores rebuilt successfully"}
    except Exception as e:
        logger.error(f"✗ Reindexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")


# ✅ 清空历史端点
@app.post("/clear-history")
async def clear_history():
    """Clear chat history"""
    agent.chat_history = []
    logger.info("✓ Chat history cleared")
    return {"status": "success", "message": "Chat history cleared"}


# ✅ 获取历史端点
@app.get("/history")
async def get_history():
    """Get current chat history"""
    return {"history": agent.chat_history}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)