import threading
import time

from openai import AuthenticationError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from PDFAgent import PdfRAGAgent


app = FastAPI(title="Academic RAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = PdfRAGAgent()


class QueryRequest(BaseModel):
    prompt: str


@app.on_event("startup")
async def startup_event():
    if not agent.index_exists():
        agent.index_status = "building"
        threading.Thread(target=agent.rebuild_index, daemon=True).start()


@app.post("/chat")
async def chat(request: QueryRequest):
    try:
        return agent.answer(request.prompt)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenRouter authentication failed. Please configure a valid OPENROUTER_API_KEY or LEO_API_KEY.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/reindex")
async def reindex():
    if agent.index_status == "building":
        return {"message": "Index build already in progress", "index_status": agent.index_status}

    agent.index_status = "building"
    threading.Thread(target=agent.rebuild_index, daemon=True).start()
    return {"message": "Index build started", "index_status": agent.index_status}


@app.get("/health")
async def health():
    elapsed_seconds = None
    if agent.index_status == "building" and agent.index_started_at:
        elapsed_seconds = round(time.time() - agent.index_started_at, 2)
    elif agent.index_duration_seconds is not None:
        elapsed_seconds = agent.index_duration_seconds

    return {
        "status": "ok",
        "index_ready": agent.index_exists() and agent.index_status == "ready",
        "index_status": agent.index_status,
        "index_error": agent.index_error,
        "index_started_at": agent.index_started_at,
        "index_finished_at": agent.index_finished_at,
        "index_elapsed_seconds": elapsed_seconds,
        "indexed_pdf_count": agent.indexed_pdf_count,
        "pdfs_folder": agent.pdfs_folder,
        "history_count": len(agent.chat_history),
        "model": agent.openrouter_model,
        "timeout_seconds": agent.openrouter_timeout,
    }


@app.get("/history")
async def history():
    return {"chat_history": agent.chat_history}


@app.post("/clear-history")
async def clear_history():
    agent.chat_history = []
    return {"message": "History cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
