import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

class Document:
    """Represents an ingested post-mortem or security document."""
    def __init__(self, content: str, metadata: Dict[str, Any], doc_id: str):
        self.content = content
        self.metadata = metadata
        self.doc_id = doc_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "metadata": self.metadata
        }

class DocumentLoader:
    """Loads markdown, text, and PDF documents from filesystem or byte streams."""

    # Curated, professional display titles for all protocol exploits & reports
    CLEAN_PROTOCOL_TITLES: Dict[str, str] = {
        "gmx exchange hack explained": "GMX Exchange (Arbitrum GLP Exploit)",
        "the sherlock web3 security report q1": "Sherlock Security (Q1 2024 Audit Cases)",
        "what is a flashloan attack": "Flashloan Attack Patterns (Sherlock Guide)",
        "cross-chain security in 2026": "Cross-Chain Security (Bridge Invariants)",
        "euler_finance": "Euler Finance",
        "curve_vyper": "Curve Finance (Vyper Reentrancy)",
        "cream_finance": "Cream Finance",
        "platypus_finance": "Platypus Finance",
        "mango_markets": "Mango Markets",
        "nomad_bridge": "Nomad Bridge",
        "beanstalk_farms": "Beanstalk Farms",
        "wormhole_bridge": "Wormhole Bridge",
        "harvest_finance": "Harvest Finance",
        "hundred_finance": "Hundred Finance",
        "saddle_finance": "Saddle Finance",
        "the_dao": "The DAO"
    }

    @classmethod
    def extract_metadata_from_text(cls, text: str, filename: str) -> Dict[str, Any]:
        """Extract metadata fields from Markdown headers or incident overviews."""
        base_name = Path(filename).stem.strip()
        clean_proto = cls.CLEAN_PROTOCOL_TITLES.get(base_name.lower())
        if not clean_proto:
            clean_proto = base_name.replace("_", " ").title()

        meta = {
            "filename": filename,
            "protocol": clean_proto,
            "loss_amount": "Unknown",
            "incident_date": "Unknown",
            "vulnerability_category": "Smart Contract Vulnerability",
            "sources": "Official Security Audit / DeFiHackLabs"
        }

        # Regex patterns for markdown metadata
        protocol_match = re.search(r"Protocol\*?:\s*([^\n\r]+)", text, re.IGNORECASE)
        if protocol_match:
            raw_proto = protocol_match.group(1).strip()
            # If in clean titles, standardize
            meta["protocol"] = cls.CLEAN_PROTOCOL_TITLES.get(raw_proto.lower(), raw_proto)

        loss_match = re.search(r"Loss Amount\*?:\s*([^\n\r]+)", text, re.IGNORECASE)
        if loss_match:
            meta["loss_amount"] = loss_match.group(1).strip()

        date_match = re.search(r"Incident Date\*?:\s*([^\n\r]+)", text, re.IGNORECASE)
        if date_match:
            meta["incident_date"] = date_match.group(1).strip()

        vuln_match = re.search(r"Vulnerability Category\*?:\s*([^\n\r]+)", text, re.IGNORECASE)
        if vuln_match:
            meta["vulnerability_category"] = vuln_match.group(1).strip()

        source_match = re.search(r"Official Sources\*?:\s*([^\n\r]+)", text, re.IGNORECASE)
        if source_match:
            meta["sources"] = source_match.group(1).strip()

        return meta

    @classmethod
    def load_file(cls, file_path: Path) -> Optional[Document]:
        """Load a single file from disk."""
        if not file_path.exists():
            return None

        ext = file_path.suffix.lower()
        content = ""

        if ext in [".md", ".txt"]:
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = file_path.read_text(encoding="latin-1")
        elif ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(file_path))
                pages = [page.extract_text() or "" for page in reader.pages]
                content = "\n\n".join(pages)
            except Exception as e:
                print(f"Error reading PDF {file_path.name}: {e}")
                return None
        elif ext == ".docx":
            try:
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(str(file_path)) as z:
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    paragraphs = []
                    for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                        texts = [node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                        if texts:
                            paragraphs.append("".join(texts))
                    content = "\n\n".join(paragraphs)
            except Exception as e:
                print(f"Error reading DOCX {file_path.name}: {e}")
                return None
        else:
            return None

        if not content.strip():
            return None

        metadata = cls.extract_metadata_from_text(content, file_path.name)
        return Document(content=content, metadata=metadata, doc_id=file_path.stem)

    @classmethod
    def load_directory(cls, dir_path: Path) -> List[Document]:
        """Load all supported documents from a directory."""
        if not dir_path.exists():
            return []

        documents = []
        for file_path in sorted(dir_path.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in [".md", ".txt", ".pdf", ".docx"]:
                doc = cls.load_file(file_path)
                if doc:
                    documents.append(doc)
        return documents

    @classmethod
    def load_from_upload(cls, filename: str, file_bytes: bytes) -> Optional[Document]:
        """Load a document from Streamlit's file uploader."""
        ext = Path(filename).suffix.lower()
        content = ""

        if ext in [".md", ".txt"]:
            try:
                content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = file_bytes.decode("latin-1")
        elif ext == ".pdf":
            try:
                import io
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                pages = [page.extract_text() or "" for page in reader.pages]
                content = "\n\n".join(pages)
            except Exception as e:
                print(f"Error parsing uploaded PDF: {e}")
                return None
        elif ext == ".docx":
            try:
                import io
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    paragraphs = []
                    for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                        texts = [node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                        if texts:
                            paragraphs.append("".join(texts))
                    content = "\n\n".join(paragraphs)
            except Exception as e:
                print(f"Error parsing uploaded DOCX: {e}")
                return None
        else:
            return None

        if not content.strip():
            return None

        metadata = cls.extract_metadata_from_text(content, filename)
        return Document(content=content, metadata=metadata, doc_id=Path(filename).stem)
