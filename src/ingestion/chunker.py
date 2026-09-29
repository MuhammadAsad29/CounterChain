import re
from typing import List, Dict, Any
from src.ingestion.document_loader import Document

class Chunk:
    """Represents a discrete semantic chunk of a document."""
    def __init__(self, chunk_id: str, text: str, metadata: Dict[str, Any]):
        self.chunk_id = chunk_id
        self.text = text
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "metadata": self.metadata
        }

class CodeAwareChunker:
    """
    Splits post-mortem documents preserving markdown section hierarchy,
    Solidity code blocks, and key invariant definitions.
    """
    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: Document) -> List[Chunk]:
        """Split a Document into coherent semantic chunks."""
        text = doc.content
        lines = text.splitlines()

        chunks: List[Chunk] = []
        current_section = "General"
        buffer: List[str] = []
        current_length = 0
        chunk_idx = 0

        # Pattern for markdown headers
        header_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

        for line in lines:
            header_match = header_pattern.match(line.strip())
            if header_match:
                current_section = header_match.group(2).strip()

            line_len = len(line) + 1 # +1 for newline

            # If adding this line exceeds chunk_size and buffer is not empty
            if current_length + line_len > self.chunk_size and buffer:
                chunk_text = "\n".join(buffer).strip()
                if chunk_text:
                    chunk_meta = dict(doc.metadata)
                    chunk_meta["section"] = current_section
                    chunk_meta["chunk_index"] = chunk_idx
                    chunk_id = f"{doc.doc_id}_c{chunk_idx:03d}"
                    chunks.append(Chunk(chunk_id=chunk_id, text=chunk_text, metadata=chunk_meta))
                    chunk_idx += 1

                # Calculate overlap: keep the tail of the buffer up to chunk_overlap chars
                overlap_buffer: List[str] = []
                overlap_len = 0
                for prev_line in reversed(buffer):
                    if overlap_len + len(prev_line) <= self.chunk_overlap:
                        overlap_buffer.insert(0, prev_line)
                        overlap_len += len(prev_line) + 1
                    else:
                        break

                buffer = overlap_buffer
                current_length = sum(len(l) + 1 for l in buffer)

            buffer.append(line)
            current_length += line_len

        # Flush remaining buffer
        if buffer:
            chunk_text = "\n".join(buffer).strip()
            if chunk_text:
                chunk_meta = dict(doc.metadata)
                chunk_meta["section"] = current_section
                chunk_meta["chunk_index"] = chunk_idx
                chunk_id = f"{doc.doc_id}_c{chunk_idx:03d}"
                chunks.append(Chunk(chunk_id=chunk_id, text=chunk_text, metadata=chunk_meta))

        return chunks

    def chunk_documents(self, documents: List[Document]) -> List[Chunk]:
        """Process multiple documents in batch."""
        all_chunks = []
        for doc in documents:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks
