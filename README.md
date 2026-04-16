# PDF Agent: Academic PDF Question Answering System Based on Retrieval-Augmented Generation

## Abstract

PDF Agent is an academic question-answering system for scholarly PDF collections. It combines PDF text extraction, document cleaning, dense retrieval, FAISS indexing, and a large language model interface to answer research questions with cited evidence from the indexed papers. The system is designed for course projects, reproducible demonstrations, and small-scale literature exploration workflows where answers should remain grounded in retrieved document passages.

## Keywords

Retrieval-augmented generation; academic PDF question answering; scholarly document processing; FAISS; dense retrieval; citation-grounded answer generation.

## System Overview

The project contains a Python backend and a Vue frontend.

- The backend extracts text from PDFs, cleans noisy scholarly-document content, builds abstract-level and full-text FAISS indexes, retrieves relevant passages, and calls an OpenRouter-compatible chat model.
- The frontend provides a research workspace with login, chat history, index status, evidence display, import/export, and reindex controls.
- The generated answers are constrained by a system prompt that requires citation markers, evidence-grounded claims, and explicit uncertainty when retrieved context is insufficient.

## Method

1. **Document ingestion**: PDFs in `pdfs/` are parsed with `PyPDF2`.
2. **Text normalization**: `text_cleaner.py` removes page artifacts, repeated headers/footers, OCR spacing noise, broken hyphenation, and reference sections for indexing.
3. **Hierarchical retrieval**: `PDFAgent.py` builds separate FAISS indexes for abstracts and full text. Abstract retrieval first selects likely source papers; full-text retrieval then searches the selected sources.
4. **Query-aware reranking**: Queries about methods, experiments, datasets, figures, limitations, or comparisons are expanded and reranked with task-specific keywords.
5. **Grounded generation**: The final answer is generated from retrieved passages only and returned with `RAG_RESULT` references containing source file names, page numbers, and evidence snippets.

## Repository Structure

```text
.
├── PDFAgent.py                 # Core RAG pipeline and answer generation
├── api.py                      # FastAPI service
├── run_all.py                  # One-command local launcher
├── text_cleaner.py             # PDF text cleaning utilities
├── requirements.txt            # Python dependencies
├── pdfs/                       # Academic PDF corpus
├── faiss_abstract/             # Abstract-level FAISS index
├── faiss_full/                 # Full-text FAISS index
├── index_cache.json            # Parsed-document cache
└── pdf-agent-frontend/         # Vue 3 + Vite frontend
```

## Requirements

- Python 3.10 or later
- Node.js and npm
- An OpenRouter API key

The backend reads the model key in the following order:

1. `OPENROUTER_API_KEY` environment variable
2. `.secrets/openrouter_api_key.txt`
3. `.env`

Secrets are intentionally ignored by Git.

## Quick Start

Create a local environment file and add your key:

```bash
cp .env.example .env
```

Then edit `.env` and set `OPENROUTER_API_KEY`.

Start both backend and frontend:

```bash
python3 run_all.py
```

The launcher creates the Python virtual environment if needed, installs backend and frontend dependencies, starts the FastAPI backend, waits for the PDF index to be ready, and starts the Vue frontend.

Default local services:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

The frontend demo account is:

```text
Username: admin1
Password: admin1
```

## Manual Backend Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000
```

Useful endpoints:

- `GET /health`: backend and index status
- `POST /chat`: answer a question from retrieved PDF evidence
- `POST /reindex`: rebuild FAISS indexes
- `GET /history`: inspect backend chat history
- `POST /clear-history`: clear backend chat history

## Manual Frontend Run

```bash
cd pdf-agent-frontend
npm install
VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

## Reproducibility Notes

- The committed FAISS indexes and `index_cache.json` correspond to the current PDF corpus under `pdfs/`.
- If PDFs are added, removed, or changed, call `POST /reindex` or run `python3 run_all.py` and use the frontend reindex control.
- The default OpenRouter model is `openai/gpt-4o-mini`; set `OPENROUTER_MODEL` to reproduce experiments with a different chat model.
- Answer quality depends on PDF text extraction quality, embedding coverage, and retrieved evidence completeness.

## Academic Use

This repository is structured as a research software artifact. When reporting results, please describe:

- The PDF corpus used for indexing
- The embedding model and chat model
- The retrieval settings and index state
- The exact prompts or evaluation questions
- Any observed cases of insufficient or ambiguous evidence

## Citation

If you use this repository in coursework, reports, or demonstrations, cite it as:

```bibtex
@software{zeng_pdf_agent_2026,
  author = {Zeng, Carter},
  title = {PDF Agent: Academic PDF Question Answering System Based on Retrieval-Augmented Generation},
  year = {2026},
  url = {https://github.com/CarterZeng/pdf_agent}
}
```

GitHub can also read the citation metadata from `CITATION.cff`.

## Limitations

The system is intended for evidence-grounded assistance over a local PDF corpus. It should not be treated as a source of facts beyond the retrieved passages. Ambiguous questions, OCR errors, tables, figures, mathematical notation, and low-quality PDF extraction can reduce retrieval and answer accuracy.
