# PDF Agent Frontend

This directory contains the Vue 3 + Vite interface for PDF Agent, an academic PDF question-answering system based on retrieval-augmented generation.

## Features

- Research workspace for asking questions about indexed academic PDFs
- Evidence panel showing retrieved references and page numbers
- Index health display and reindex control
- Local chat history with import and export
- Demonstration login flow for classroom or project presentation use

## Development

Install dependencies:

```bash
npm install
```

Run the frontend against a local backend:

```bash
VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

Build production assets:

```bash
npm run build
```

The full project can also be launched from the repository root with:

```bash
python3 run_all.py
```
