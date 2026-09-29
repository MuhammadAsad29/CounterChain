import os
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
from src.ingestion.chunker import Chunk

class FAISSVectorStore:
    """
    In-memory and disk-persisted FAISS vector store with automated NumPy fallback.
    Guarantees seamless execution on local systems and free-tier cloud platforms.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.chunks: List[Chunk] = []
        self.embeddings: np.ndarray = np.empty((0, dimension), dtype=np.float32)
        self.index = None
        self._faiss_available = False
        self._init_index()

    def _init_index(self):
        try:
            import faiss
            # IndexFlatIP computes exact inner product (Cosine similarity on normalized vectors)
            self.index = faiss.IndexFlatIP(self.dimension)
            self._faiss_available = True
        except ImportError:
            self._faiss_available = False
            self.index = None

    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray):
        """Add chunks and corresponding normalized vector embeddings to the index."""
        if len(chunks) == 0:
            return

        self.chunks.extend(chunks)
        if self.embeddings.shape[0] == 0:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])

        if self._faiss_available and self.index is not None:
            self.index.add(embeddings)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """
        Search for top_k most similar chunks.
        Returns list of (Chunk, similarity_score).
        """
        if len(self.chunks) == 0:
            return []

        actual_k = min(top_k, len(self.chunks))

        if self._faiss_available and self.index is not None:
            # FAISS search
            scores, indices = self.index.search(query_embedding, actual_k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.chunks) and idx >= 0:
                    results.append((self.chunks[idx], float(score)))
            return results
        else:
            # High-performance NumPy Cosine similarity fallback
            # query_embedding shape: (1, dim), self.embeddings shape: (N, dim)
            sims = np.dot(self.embeddings, query_embedding.T).flatten()
            top_indices = np.argsort(sims)[::-1][:actual_k]
            results = []
            for idx in top_indices:
                results.append((self.chunks[idx], float(sims[idx])))
            return results

    def save(self, directory: Path):
        """Persist index and metadata to disk."""
        directory.mkdir(parents=True, exist_ok=True)
        meta_file = directory / "chunks_metadata.json"
        
        # Serialize chunks
        data = [chunk.to_dict() for chunk in self.chunks]
        meta_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Save embeddings numpy array
        np.save(directory / "embeddings.npy", self.embeddings)

        # Save FAISS index binary if available
        if self._faiss_available and self.index is not None:
            import faiss
            faiss.write_index(self.index, str(directory / "faiss_index.bin"))

    def load(self, directory: Path) -> bool:
        """Load index and metadata from disk."""
        meta_file = directory / "chunks_metadata.json"
        embed_file = directory / "embeddings.npy"
        faiss_file = directory / "faiss_index.bin"

        if not (meta_file.exists() and embed_file.exists()):
            return False

        try:
            raw_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            self.chunks = [
                Chunk(chunk_id=c["chunk_id"], text=c["text"], metadata=c["metadata"])
                for c in raw_meta
            ]
            self.embeddings = np.load(embed_file)

            if self._faiss_available and faiss_file.exists():
                import faiss
                self.index = faiss.read_index(str(faiss_file))
            else:
                self._init_index()
                if self._faiss_available and self.index is not None:
                    self.index.add(self.embeddings)

            return True
        except Exception as e:
            print(f"Error loading vector index: {e}")
            return False
