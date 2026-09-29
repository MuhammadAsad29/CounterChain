from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from src.ingestion.chunker import Chunk
from src.retrieval.embedder import BGEEmbedder
from src.retrieval.vector_store import FAISSVectorStore
from src.retrieval.bm25_search import BM25Searcher

class HybridRetriever:
    """
    Hybrid Retrieval Engine combining BGE dense semantic vector search
    with BM25 lexical keyword search via Reciprocal Rank Fusion (RRF).
    """
    def __init__(
        self,
        vector_store: FAISSVectorStore,
        embedder: BGEEmbedder,
        chunks: List[Chunk]
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.chunks = chunks
        self.bm25_searcher = BM25Searcher(chunks)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        protocol_filter: Optional[str] = None,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Execute hybrid search and merge rankings with Reciprocal Rank Fusion.
        Returns sorted list of dictionaries with chunk text, metadata, and scores.
        """
        # 1. Dense Semantic Search
        query_vec = self.embedder.embed_query(query)
        dense_results = self.vector_store.search(query_vec, top_k=top_k * 2)

        # 2. Sparse BM25 Search
        sparse_results = self.bm25_searcher.search(query, top_k=top_k * 2)

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores = defaultdict(float)
        chunk_map: Dict[str, Chunk] = {}
        dense_ranks = {}
        sparse_ranks = {}

        for rank, (chunk, score) in enumerate(dense_results):
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            dense_ranks[cid] = rank + 1
            rrf_scores[cid] += dense_weight * (1.0 / (rrf_k + rank + 1))

        for rank, (chunk, score) in enumerate(sparse_results):
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            sparse_ranks[cid] = rank + 1
            rrf_scores[cid] += sparse_weight * (1.0 / (rrf_k + rank + 1))

        # 4. Filter by protocol if requested
        candidates = []
        for cid, score in rrf_scores.items():
            chunk = chunk_map[cid]
            if protocol_filter and protocol_filter.lower() != "all":
                doc_proto = chunk.metadata.get("protocol", "").lower()
                if protocol_filter.lower() not in doc_proto:
                    continue
            candidates.append((chunk, score))

        # Sort descending by RRF score
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:top_k]

        # 5. Format results with source attribution
        formatted = []
        for rank, (chunk, score) in enumerate(top_candidates):
            formatted.append({
                "rank": rank + 1,
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "protocol": chunk.metadata.get("protocol", "Unknown"),
                "section": chunk.metadata.get("section", "General"),
                "loss_amount": chunk.metadata.get("loss_amount", "N/A"),
                "vulnerability_category": chunk.metadata.get("vulnerability_category", "N/A"),
                "sources": chunk.metadata.get("sources", "DeFiHackLabs / Rekt.news"),
                "rrf_score": round(score, 5),
                "dense_rank": dense_ranks.get(chunk.chunk_id, None),
                "sparse_rank": sparse_ranks.get(chunk.chunk_id, None)
            })

        return formatted
