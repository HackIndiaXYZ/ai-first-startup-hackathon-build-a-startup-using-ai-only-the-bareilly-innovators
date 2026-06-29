"""
Sivi — RAG Engine
Handles ingestion of documents (PDF, TXT, MD) and semantic search querying.
"""

import os
import glob
import logging
import uuid
import chromadb
from text_llm import text_llm

logger = logging.getLogger("sivi.rag_engine")

class RAGEngine:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.docs_dir = os.path.join(self.data_dir, "documents")
        os.makedirs(self.docs_dir, exist_ok=True)
        self.chroma_path = os.path.join(self.data_dir, "chroma")
        
        try:
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            self.collection = self.client.get_or_create_collection(name="sivi_documents")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB for RAG: {e}")
            self.client = None
            self.collection = None

    def ingest_directory(self) -> int:
        """Scan the documents directory and ingest new files."""
        if not self.collection: return 0
        
        added_count = 0
        for ext in ["*.txt", "*.md", "*.pdf"]:
            for file_path in glob.glob(os.path.join(self.docs_dir, ext)):
                if self._ingest_file(file_path):
                    added_count += 1
        return added_count

    def _ingest_file(self, file_path: str) -> bool:
        """Ingest a single file. Returns True if successfully added."""
        filename = os.path.basename(file_path)
        
        # Check if already ingested by checking metadata
        existing = self.collection.get(where={"filename": filename})
        if existing['ids']:
            return False # Already ingested
            
        try:
            content = self._extract_text(file_path)
            if not content: return False
            
            # Simple chunking (by paragraphs)
            chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 50]
            
            if not chunks:
                chunks = [content[:1000]] # Fallback to single chunk
                
            ids = [str(uuid.uuid4()) for _ in chunks]
            metadatas = [{"filename": filename} for _ in chunks]
            
            self.collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Ingested {filename} ({len(chunks)} chunks)")
            return True
        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {e}")
            return False

    def _extract_text(self, file_path: str) -> str:
        """Extract text from supported file types."""
        if file_path.endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                return "\n\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            except ImportError:
                logger.error("pypdf not installed.")
                return ""
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

    def query(self, query_text: str, n_results: int = 3) -> str:
        """Retrieve relevant context for a query."""
        if not self.collection: return ""
        try:
            results = self.collection.query(query_texts=[query_text], n_results=n_results)
            if results['documents'] and results['documents'][0]:
                docs = results['documents'][0]
                return "\n---\n".join(docs)
        except Exception as e:
            logger.error(f"Error querying RAG: {e}")
        return ""

    async def answer_question(self, question: str) -> str:
        """Query the vector database and generate an answer using the text LLM."""
        context = self.query(question)
        if not context:
            return "I couldn't find any relevant information in your documents."
            
        prompt = f"Context information is below.\n---------------------\n{context}\n---------------------\nGiven the context information and not prior knowledge, answer the following question: {question}"
        
        system = "You are Sivi, an elite AI assistant. Answer based only on the provided context. If the context does not contain the answer, say 'I cannot find the answer in the provided documents.'"
        
        return await text_llm.complete(prompt=prompt, system=system)


rag_engine = RAGEngine()
