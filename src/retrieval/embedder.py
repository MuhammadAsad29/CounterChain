from typing import List, Union
import numpy as np
from src.config import EMBEDDING_MODEL_NAME

class BGEEmbedder:
    """
    Lightweight embedding generator using BAAI/bge-small-en-v1.5.
    Optimized for CPU inference with batching and normalized embeddings.
    """
    _instance = None
    _model = None

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        if BGEEmbedder._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                BGEEmbedder._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "Missing 'sentence-transformers'! Please run in your terminal: pip install -r requirements.txt"
                )
        self.model = BGEEmbedder._model

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed document passages without query instruction prefix.
        Normalizes embeddings for direct cosine similarity via inner product.
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return np.array(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a counterfactual query using BGE's instruction prefix.
        """
        # BGE models use an asymmetric instruction prefix for queries
        if "bge" in self.model_name.lower():
            formatted_query = f"Represent this sentence for searching relevant passages: {query}"
        else:
            formatted_query = query

        embedding = self.model.encode(
            [formatted_query],
            normalize_embeddings=True
        )
        return np.array(embedding, dtype=np.float32)
