import os
import json
import logging
import uuid
import chromadb

logger = logging.getLogger("sivi.memory_vault")

class MemoryVault:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.chroma_path = os.path.join(self.data_dir, "chroma")
        
        # Legacy JSON path
        self.legacy_file = os.path.join(self.data_dir, "sivi_memory.json")
        
        try:
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            self.collection = self.client.get_or_create_collection(name="sivi_memories")
            self._migrate_legacy()
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None

    def _migrate_legacy(self):
        if not self.collection: return
        if os.path.exists(self.legacy_file):
            try:
                with open(self.legacy_file, 'r', encoding='utf-8') as f:
                    old_memories = json.load(f)
                
                if old_memories:
                    logger.info(f"Migrating {len(old_memories)} legacy memories to ChromaDB")
                    for m in old_memories:
                        self.remember(m)
                
                # Rename to avoid re-migration
                os.rename(self.legacy_file, self.legacy_file + ".bak")
            except Exception as e:
                logger.error(f"Error migrating legacy memories: {e}")

    def remember(self, fact: str) -> str:
        """Add a new fact to vector memory."""
        if not self.collection:
            return "My vector memory system is offline."
            
        try:
            # Check if already exists (exact match fallback)
            results = self.collection.get(where_document={"$contains": fact})
            if results['documents']:
                return "I already have that in my memory."
                
            self.collection.add(
                documents=[fact],
                ids=[str(uuid.uuid4())]
            )
            return "Got it, I will remember that for you."
        except Exception as e:
            logger.error(f"Error remembering fact: {e}")
            return "Failed to save to memory."

    def forget_all(self) -> str:
        """Clear all vector memories."""
        if not self.client:
            return "Memory system is offline."
            
        try:
            self.client.delete_collection("sivi_memories")
            self.collection = self.client.create_collection("sivi_memories")
            return "I have cleared my memory vault."
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
            return "Failed to clear memory."

    def query(self, query_text: str, n_results: int = 3) -> list[str]:
        """Query specific memories related to a topic."""
        if not self.collection: return []
        try:
            results = self.collection.query(query_texts=[query_text], n_results=n_results)
            if results['documents'] and results['documents'][0]:
                return results['documents'][0]
        except Exception as e:
            logger.error(f"Error querying memory: {e}")
        return []

    def get_memory_context(self) -> str:
        """Returns the memory block to inject into the system prompt."""
        if not self.collection:
            return ""
        try:
            # Get all documents (limited to 20 for prompt size safety)
            results = self.collection.get(limit=20)
            docs = results.get('documents', [])
            if not docs:
                return ""
            
            return "THINGS YOU MUST REMEMBER ABOUT THE USER:\n- " + "\n- ".join(docs)
        except Exception as e:
            logger.error(f"Error getting memory context: {e}")
            return ""

memory_vault = MemoryVault()
