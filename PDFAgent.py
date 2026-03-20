import os
import re
from typing import List
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# --- 嵌入模型包装类 ---
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        texts = ["passage: " + t for t in texts]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        text = "query: " + text
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()


# --- RAG 核心类 ---
class PdfRAGAgent:
    def __init__(
            self,
            model_name: str = "BAAI/bge-base-en-v1.5",
            temperature: float = 0,
            pdfs_folder: str = "./pdfs"
    ):
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

        # 存储对话历史，使用 LangChain 的消息对象
        self.chat_history = []


    def extract_abstract(self, text: str) -> str | None:
        pattern = r"Abstract(.*?)(Introduction|1\.|I\.)"
        match = re.search(pattern, text, re.S | re.I)
        return match.group(1).strip() if match else None

    def load_pdfs_from_folder(self, folder_path: str) -> List[str]:
        return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".pdf")]

    def extract_pdf_text(self, pdf_path: str) -> str:
        text = ""
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text: text += page_text + "\n"
        return text

    def split_text(self, text: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=100, separators=["\n\n", "\n", ".", " ", ""]
        )
        return splitter.split_text(text)

    def load_abstract_store(self):
        return FAISS.load_local(self.abstract_path, self.embeddings, allow_dangerous_deserialization=True)

    def load_fulltext_store(self):
        return FAISS.load_local(self.fulltext_path, self.embeddings, allow_dangerous_deserialization=True)

    def build_vector_store_from_pdfs(self):
        pdf_paths = self.load_pdfs_from_folder(self.pdfs_folder)
        abstract_texts, abstract_metadatas = [], []
        full_texts, full_metadatas = [], []

        for pdf_path in pdf_paths:
            print(f"Processing: {pdf_path}")
            text = self.extract_pdf_text(pdf_path)
            filename = os.path.basename(pdf_path)

            abstract = self.extract_abstract(text)
            if abstract:
                abstract_texts.append(abstract)
                abstract_metadatas.append({"source": filename})

            chunks = self.split_text(text)
            for chunk in chunks:
                full_texts.append(chunk)
                full_metadatas.append({"source": filename})

        FAISS.from_texts(abstract_texts, self.embeddings, metadatas=abstract_metadatas).save_local(self.abstract_path)
        FAISS.from_texts(full_texts, self.embeddings, metadatas=full_metadatas).save_local(self.fulltext_path)
        print("Indexes built.")

    def hierarchical_retrieve(self, query: str):
        abstract_store = self.load_abstract_store()
        full_store = self.load_fulltext_store()

        # 阶段 1: 检索摘要
        abstract_docs = abstract_store.similarity_search(query, k=3)
        candidate_sources = list(set(doc.metadata["source"] for doc in abstract_docs))

        # 阶段 2: 检索全文
        # 注意：FAISS 的 filter 接收一个 callable。
        def metadata_filter(metadata):
            return metadata.get("source") in candidate_sources

        full_docs = full_store.similarity_search(
            query,
            k=5,
            filter=metadata_filter if candidate_sources else None
        )
        return full_docs

    def get_chat_history_string(self):
        """将消息对象转换为字符串格式"""
        buffer = ""
        for msg in self.chat_history:
            if isinstance(msg, HumanMessage):
                buffer += f"User: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                buffer += f"Assistant: {msg.content}\n"
        return buffer

    def answer(self, query: str):
        # 1. Retrieve relevant document chunks
        docs = self.hierarchical_retrieve(query)

        if not docs:
            return "I'm sorry, but no relevant information was found in the provided documents."

        # 2. Construct context for the LLM and prepare raw snippets for user display
        context_blocks = []
        raw_highlights = []  # To store the original text for the user

        for i, d in enumerate(docs):
            ref_id = i + 1
            # Handling the 'None' page issue by providing a fallback
            page_val = d.metadata.get('page')
            page_info = f"Page {page_val}" if page_val else "Abstract/Front Matter"
            source_info = f"{d.metadata['source']} ({page_info})"

            # Context passed to the LLM
            context_blocks.append(f"--- REFERENCE {ref_id} ({source_info}) ---\n{d.page_content}")

            # Original text snippets displayed to the user
            raw_highlights.append(f"【Snippet {ref_id} | Source: {source_info}】\n{d.page_content.strip()}")

        context = "\n\n".join(context_blocks)

        # 3. Construct conversation history string
        history_str = ""
        for msg in self.chat_history:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            history_str += f"{role}: {msg.content}\n"

        # 4. Construct the System Prompt in English
        system_prompt = f"""You are a precise academic research assistant. 
        Answer the user's question based ONLY on the provided RAG context. 
        Always cite the reference numbers, such as [1] or [2], when mentioning specific facts.
        If the context does not contain the answer, state that it cannot be determined.

        [CONVERSATION HISTORY]
        {history_str}

        [RAG CONTEXT]
        {context}
        """

        # 5. Invoke the LLM
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])

        answer_text = response.content

        # 6. Update chat history (Limit to last 10 messages to manage context window)
        self.chat_history.append(HumanMessage(content=query))
        self.chat_history.append(AIMessage(content=answer_text))
        if len(self.chat_history) > 10:
            self.chat_history = self.chat_history[-10:]

        # 7. Concatenate final output: AI Answer + Evidence Highlights
        final_output = (
                f"### AI Response\n{answer_text}\n\n"
                f"--- \n"
                f"### Retrieved Evidence (RAG Content)\n"
                + "\n\n".join(raw_highlights)
        )

        return final_output


def main():
    # 确保文件夹存在
    if not os.path.exists("./pdfs"):
        os.makedirs("./pdfs")

    agent = PdfRAGAgent()

    # 如果是第一次运行，取消下面注释来建立索引
    # agent.build_vector_store_from_pdfs()

    print("--- Academic RAG System Ready  ---")

    while True:
        query = input("\nUser: ")
        if query.lower() in ["exit", "quit", "退出"]:
            break

        if not query.strip():
            continue

        result = agent.answer(query)
        print(f"\nAssistant: {result}")


if __name__ == "__main__":
    main()