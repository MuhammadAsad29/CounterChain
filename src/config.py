import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_REPORTS_DIR = DATA_DIR / "raw_reports"
PROCESSED_INDEX_DIR = DATA_DIR / "processed_index"

# Automatically load .env from workspace or parent directory
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "..env")

def get_api_key() -> str:
    """
    Retrieve OpenRouter API key.
    Prioritizes Streamlit secrets (for cloud deployment), then environment variables.
    """
    # 1. Check Streamlit cloud secrets if running inside Streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "OPENROUTER_API_KEY" in st.secrets:
            return st.secrets["OPENROUTER_API_KEY"].strip()
    except Exception:
        pass

    # 2. Check standard environment variables
    env_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if env_key:
        return env_key

    # 3. Check fallback ..env directly if not populated into env
    parent_env = BASE_DIR / "..env"
    if parent_env.exists():
        content = parent_env.read_text(encoding="utf-8").strip()
        if content.startswith("sk-or-"):
            return content.splitlines()[0].strip()

    return ""

# Model configurations
OPENROUTER_API_KEY = get_api_key()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

# Embedding & Retrieval configurations
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
TOP_K_DEFAULT = int(os.getenv("TOP_K", "5"))
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

# Supported document types
SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}

# Verified active free models on OpenRouter
FALLBACK_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "openrouter/free"
]
