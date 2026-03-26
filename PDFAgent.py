import hashlib
import json
import os
import re
import shutil
import threading
import time
from typing import Any, Dict, List

from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from text_cleaner import clean_for_index, clean_for_output


class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        texts = ["passage: " + t for t in texts]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(["query: " + text], normalize_embeddings=True)
        return embedding[0].tolist()


def is_comparison_query(query: str) -> bool:
    q = query.lower()
    keywords = [
        "compare", "comparison", "difference", "different",
        "similarity", "similarities", "contrast",
        "between the two papers", "both papers", "two papers",
    ]
    return any(k in q for k in keywords)


def rewrite_query_for_retrieval(query: str) -> str:
    q = query.lower()

    if any(x in q for x in ["table", "figure", "fig.", "fig ", "chart"]):
        return query + " table figure fig results experiment caption"

    if any(x in q for x in ["method", "approach", "propose", "proposed"]):
        return query + " proposed method approach strategy objective pipeline filtering blacklist whitelist labeling n-gram"

    if any(x in q for x in ["evaluation", "evaluate", "metric", "precision", "recall", "result", "results"]):
        return query + " evaluation metric precision recall experiment test relevance result"

    if any(x in q for x in ["dataset", "data", "corpus"]):
        return query + " dataset corpus data source benchmark training test set"

    if any(x in q for x in ["contribution", "main idea", "summary"]):
        return query + " contribution objective main idea proposed approach"

    return query


def should_force_single_source(query: str) -> bool:
    if is_comparison_query(query):
        return False

    q = query.lower()
    triggers = [
        "the paper", "this paper", "the study", "this study",
        "the article", "this article",
    ]
    return any(t in q for t in triggers)


def get_distinct_sources(docs):
    sources = []
    for d in docs:
        src = d.metadata.get("source")
        if src and src not in sources:
            sources.append(src)
    return sources


def filter_docs_for_question(docs, question: str):
    q = question.lower()

    if any(x in q for x in ["method", "approach", "propose", "proposed"]):
        bad_words = [
            "precision", "recall", "evaluation",
            "high relevancy", "medium relevancy", "low relevancy",
            "table", "dissemination",
        ]
        filtered = []
        for d in docs:
            text = d.page_content.lower()
            bad_hits = sum(1 for w in bad_words if w in text)
            if bad_hits >= 2:
                continue
            filtered.append(d)
        return filtered if filtered else docs

    return docs


def rerank_docs_by_question(docs, question: str):
    q = question.lower()

    if any(x in q for x in ["table", "figure", "fig.", "fig ", "chart"]):
        keywords = ["table", "figure", "fig", "result", "caption", "experiment"]
    elif any(x in q for x in ["method", "approach", "propose", "proposed"]):
        keywords = [
            "propose", "proposed", "method", "approach", "strategy",
            "objective", "pipeline", "blacklist", "whitelist",
            "filtering", "labeling", "n-gram",
        ]
    elif any(x in q for x in ["evaluation", "evaluate", "metric", "precision", "result", "results"]):
        keywords = ["precision", "recall", "evaluation", "metric", "experiment", "relevance", "result"]
    elif any(x in q for x in ["dataset", "data", "corpus"]):
        keywords = ["dataset", "data", "corpus", "training", "test"]
    elif any(x in q for x in ["contribution", "main idea", "summary"]):
        keywords = ["contribution", "objective", "proposed", "approach", "study", "paper"]
    else:
        keywords = []

    scored = []
    for d in docs:
        text = d.page_content.lower()
        score = sum(1 for kw in keywords if kw in text)
        scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored]


class PdfRAGAgent:
    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        temperature: float = 0,
        pdfs_folder: str = "./pdfs",
    ):
        self.pdfs_folder = pdfs_folder
        self.abstract_path = "faiss_abstract"
        self.fulltext_path = "faiss_full"
        self.index_cache_path = "index_cache.json"
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.openrouter_timeout = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "60"))
        self.openrouter_max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "420"))

        self.embeddings = SentenceTransformerEmbeddings(model_name)
        self.llm = ChatOpenAI(
            model=self.openrouter_model,
            base_url="https://openrouter.ai/api/v1",
            api_key="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",
            temperature=temperature,
            timeout=self.openrouter_timeout,
            max_tokens=self.openrouter_max_tokens,
            max_retries=1,
        )

        self.chat_history = []
        self.index_lock = threading.Lock()
        self.index_status = "ready" if self.index_exists() else "missing"
        self.index_error = None
        self.index_started_at = None
        self.index_finished_at = time.time() if self.index_exists() else None
        self.index_duration_seconds = 0 if self.index_exists() else None
        self.indexed_pdf_count = 0

    def extract_abstract(self, text: str) -> str | None:
        pattern = r"Abstract(.*?)(Introduction|1\.|I\.)"
        match = re.search(pattern, text, re.S | re.I)
        return match.group(1).strip() if match else None

    def get_pdf_signature(self, path: str) -> str:
        stat = os.stat(path)
        signature = f"{os.path.basename(path)}:{stat.st_size}:{stat.st_mtime_ns}"
        return hashlib.sha256(signature.encode("utf-8")).hexdigest()

    def load_index_cache(self) -> dict:
        if not os.path.exists(self.index_cache_path):
            return {}
        try:
            with open(self.index_cache_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def save_index_cache(self, cache: dict) -> None:
        with open(self.index_cache_path, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=True)

    def parse_pdf_documents(self, file: str) -> dict:
        path = os.path.join(self.pdfs_folder, file)
        reader = PdfReader(path)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", " ", ""],
        )

        cover_text = "\n".join([p.extract_text() or "" for p in reader.pages[:2]])
        cover_text = clean_for_index(cover_text)

        abstract_docs = []
        abstract = self.extract_abstract(cover_text)
        if abstract:
            abstract = clean_for_index(abstract)
            if abstract.strip():
                abstract_docs.append({
                    "page_content": abstract,
                    "metadata": {"source": file, "page": 1},
                })

        full_docs = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if not page_text:
                continue

            page_text = clean_for_index(page_text)
            if not page_text.strip():
                continue

            chunks = splitter.split_text(page_text)
            for chunk in chunks:
                chunk = clean_for_index(chunk)
                if chunk.strip():
                    full_docs.append({
                        "page_content": chunk,
                        "metadata": {"source": file, "page": i + 1},
                    })

        return {
            "signature": self.get_pdf_signature(path),
            "abstract_docs": abstract_docs,
            "full_docs": full_docs,
        }

    def build_vector_store_from_pdfs(self):
        if not os.path.exists(self.pdfs_folder):
            os.makedirs(self.pdfs_folder)

        pdf_files = sorted(f for f in os.listdir(self.pdfs_folder) if f.endswith(".pdf"))
        existing_cache = self.load_index_cache()
        next_cache = {}
        all_abstract_docs = []
        all_full_chunks = []

        for file in pdf_files:
            path = os.path.join(self.pdfs_folder, file)
            signature = self.get_pdf_signature(path)
            cached = existing_cache.get(file)

            if cached and cached.get("signature") == signature:
                parsed = cached
            else:
                parsed = self.parse_pdf_documents(file)

            next_cache[file] = parsed
            all_abstract_docs.extend(
                Document(page_content=doc["page_content"], metadata=doc["metadata"])
                for doc in parsed.get("abstract_docs", [])
            )
            all_full_chunks.extend(
                Document(page_content=doc["page_content"], metadata=doc["metadata"])
                for doc in parsed.get("full_docs", [])
            )

        for path in [self.abstract_path, self.fulltext_path]:
            if os.path.exists(path):
                shutil.rmtree(path)

        if all_abstract_docs:
            FAISS.from_documents(all_abstract_docs, self.embeddings).save_local(self.abstract_path)
        if all_full_chunks:
            FAISS.from_documents(all_full_chunks, self.embeddings).save_local(self.fulltext_path)

        self.save_index_cache(next_cache)
        self.indexed_pdf_count = len(pdf_files)

    def index_exists(self) -> bool:
        return os.path.exists(self.fulltext_path) and os.path.exists(self.abstract_path)

    def ensure_index_ready(self) -> None:
        if self.index_status == "building":
            raise RuntimeError("Index is building. Please wait a moment and try again.")
        if not self.index_exists():
            detail = self.index_error or "Index not found. Please run /reindex."
            raise FileNotFoundError(detail)

    def rebuild_index(self) -> None:
        with self.index_lock:
            self.index_status = "building"
            self.index_error = None
            self.index_started_at = time.time()
            self.index_finished_at = None
            self.index_duration_seconds = None
            try:
                self.build_vector_store_from_pdfs()
            except Exception as exc:
                self.index_status = "error"
                self.index_error = f"Index build failed: {exc}"
                self.index_finished_at = time.time()
                self.index_duration_seconds = round(self.index_finished_at - self.index_started_at, 2)
                raise
            else:
                self.index_status = "ready"
                self.index_finished_at = time.time()
                self.index_duration_seconds = round(self.index_finished_at - self.index_started_at, 2)

    def load_vector_store(self, path: str):
        try:
            return FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
        except TypeError:
            return FAISS.load_local(path, self.embeddings)

    def answer(self, query: str) -> Dict[str, Any]:
        self.ensure_index_ready()
        abs_store = self.load_vector_store(self.abstract_path)
        full_store = self.load_vector_store(self.fulltext_path)

        retrieval_query = rewrite_query_for_retrieval(query)
        single_source = should_force_single_source(query)

        abs_results = abs_store.similarity_search(
            retrieval_query,
            k=1 if single_source else 3,
        )

        candidates = get_distinct_sources(abs_results)

        def filter_fn(meta):
            return meta.get("source") in candidates

        docs = full_store.similarity_search(
            retrieval_query,
            k=8 if not single_source else 6,
            filter=filter_fn if candidates else None,
        )

        docs = filter_docs_for_question(docs, query)
        docs = rerank_docs_by_question(docs, query)

        if single_source:
            top_source = candidates[0] if candidates else None
            if top_source:
                docs = [d for d in docs if d.metadata.get("source") == top_source]

        docs = docs[:4]

        rag_results = []
        context_list = []
        for i, d in enumerate(docs):
            src = d.metadata.get("source", "Unknown")
            pg = d.metadata.get("page", "N/A")
            content = clean_for_output(d.page_content.strip())
            context_list.append(f"[Ref {i + 1} | {src} P.{pg}]\n{content}")
            rag_results.append({
                "ref_id": i + 1,
                "source": src,
                "page": pg,
                "content": content,
            })

        if single_source:
            sources = [x["source"] for x in rag_results]
            if len(set(sources)) > 1:
                return {
                    "response": "The query refers to a single paper, but the retrieved context still comes from multiple papers. Please specify the paper title.",
                    "RAG_RESULT": rag_results,
                    "chat_history": self.chat_history,
                }

        history_context = "\n".join(self.chat_history)
        context_text = "\n\n".join(context_list)

        comparison_rule = ""
        if is_comparison_query(query):
            comparison_rule = "This is a comparison question. Organize the answer by paper/source first, then summarize similarities and differences."

        system_prompt = f"""You are a precise academic research assistant.

Answer the user's question based ONLY on the provided context.

Rules:
1. Answer only what is asked.
2. If the question refers to "the paper", "this paper", "the study", or "this study", answer using ONE paper only.
3. Do NOT combine findings from multiple papers unless the user explicitly asks for comparison.
4. If the question asks about method/approach, focus on the proposed method or pipeline.
5. If the question asks about evaluation, focus on metrics, experiments, and results.
6. If the question asks about dataset/data, focus on the dataset, corpus, or data source.
7. If this is a comparison question, organize the answer by paper/source first, then summarize similarities and differences.
8. Every factual sentence should include at least one citation like [1] or [2].
9. Do not place all citations only at the end of the paragraph.
10. If the context is insufficient, say so clearly.

{comparison_rule}

[HISTORY]
{history_context}

[CONTEXT]
{context_text}
"""

        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query),
        ])

        cleaned_response = clean_for_output(response.content)
        self.chat_history.append(f"User: {query}")
        self.chat_history.append(f"Assistant: {cleaned_response}")

        if len(self.chat_history) > 10:
            self.chat_history = self.chat_history[-10:]

        return {
            "response": cleaned_response,
            "RAG_RESULT": rag_results,
            "chat_history": self.chat_history,
        }
