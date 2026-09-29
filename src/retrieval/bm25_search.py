import re
import math
from collections import Counter
from typing import List, Tuple, Dict, Any
from src.ingestion.chunker import Chunk

# Attempt to import rank_bm25, with an automatic pure-Python fallback
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    class BM25Okapi:
        """
        Pure-Python fallback implementation of BM25Okapi.
        Guarantees zero-dependency execution if rank_bm25 package is not installed.
        """
        def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
            self.k1 = k1
            self.b = b
            self.corpus_size = len(corpus)
            self.doc_lengths = [len(doc) for doc in corpus]
            self.avgdl = sum(self.doc_lengths) / self.corpus_size if self.corpus_size > 0 else 1.0
            self.doc_freqs = []
            self.nd: Dict[str, int] = {}

            for doc in corpus:
                frequencies = Counter(doc)
                self.doc_freqs.append(frequencies)
                for word in frequencies.keys():
                    self.nd[word] = self.nd.get(word, 0) + 1

            self.idf: Dict[str, float] = {}
            for word, freq in self.nd.items():
                self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

        def get_scores(self, query: List[str]) -> List[float]:
            scores = [0.0] * self.corpus_size
            for q in query:
                if q not in self.idf:
                    continue
                idf_val = self.idf[q]
                for i, doc_freq in enumerate(self.doc_freqs):
                    freq = doc_freq.get(q, 0)
                    if freq > 0:
                        num = freq * (self.k1 + 1)
                        denom = freq + self.k1 * (1 - self.b + self.b * (self.doc_lengths[i] / self.avgdl))
                        scores[i] += idf_val * (num / denom)
            return scores

class BM25Searcher:
    """
    Lexical keyword retriever specialized for smart contract identifiers,
    Solidity keywords, and DeFi protocol tokens.
    """
    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks
        self.corpus = [self.tokenize(c.text) for c in chunks]
        if self.corpus:
            self.bm25 = BM25Okapi(self.corpus)
        else:
            self.bm25 = None

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """
        Tokenize code and text, splitting camelCase, snake_case, and Solidity symbols.
        Example: 'donateToReserves' -> ['donate', 'to', 'reserves', 'donatetoreserves']
        """
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
        sub_tokens = []
        for t in tokens:
            sub_tokens.append(t)
            # Split camelCase
            parts = re.findall(r"[a-z]+|[A-Z][a-z]*|[0-9]+", t)
            if len(parts) > 1:
                sub_tokens.extend([p.lower() for p in parts])
        return sub_tokens

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Perform BM25 search on query tokens."""
        if not self.bm25 or not self.chunks:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        actual_k = min(top_k, len(self.chunks))
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:actual_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((self.chunks[idx], float(scores[idx])))
        return results
