# CounterChain: A Counterfactual RAG System for DeFi Exploit Analysis

[![Streamlit Ready](https://img.shields.io/badge/Streamlit-Ready-FF4B4B?style=flat&logo=streamlit)](https://streamlit.io)
[![Model](https://img.shields.io/badge/LLM-inclusionai%2Fling--3.0--flash--fin-blue)](https://openrouter.ai)
[![Embeddings](https://img.shields.io/badge/Embeddings-BAAI%2Fbge--small--en--v1.5-green)](https://huggingface.co/BAAI/bge-small-en-v1.5)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**CounterChain** is a domain-specific Retrieval-Augmented Generation (RAG) system engineered to perform structured counterfactual reasoning over historical Decentralized Finance (DeFi) exploits.

Instead of merely retrieving historical post-mortems, CounterChain evaluates hypothetical security interventions:
> *"Would the $197M Euler Finance exploit have succeeded if reentrancy guards or strict solvency checks were enforced?"*

---

## 🎯 Key Capabilities

- **Counterfactual Causality Engine**: Contrasts the historical attack trace against the hypothetical counterfactual branch, pinning down the exact point of execution divergence.
- **Structured Security Verdicts**: Generates standardized classifications:
  - 🛡️ `PREVENTED`: Transaction reverts at divergence point (e.g. require assertion failure).
  - ⚠️ `PARTIALLY_MITIGATED`: Exploit slowed down, limited in capital extraction, or higher complexity.
  - 🚨 `VULNERABILITY_PERSISTS`: The patch fails to address the root exploit mechanism.
  - 🔄 `SHIFTED_ATTACK_VECTOR`: Patch introduces a new bypass or attack surface.
  - ❓ `INCONCLUSIVE`: Insufficient post-mortem telemetry to prove invariant state.
- **Hybrid Search (Dense BGE + Sparse BM25)**: Uses **`BAAI/bge-small-en-v1.5`** alongside **BM25Okapi** fused via **Reciprocal Rank Fusion (RRF)** to accurately retrieve both conceptual vectors and exact Solidity function signatures (`donateToReserves`, `emergencyWithdraw`).
- **100% Verified Official Dataset**: Sourced exclusively from **DeFiHackLabs GitHub (`SunWeb3Sec/DeFiHackLabs`)**, **Rekt.news**, and top security audit firms (PeckShield, OpenZeppelin, Trail of Bits, ConsenSys Diligence).
- **Automated 5-Exploit Benchmark Hub**: Pre-configured evaluation suite measuring retrieval recall, verdict agreement, and latency against expert consensus.

---

## 🧠 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       COUNTERCHAIN PIPELINE                 │
└─────────────────────────────────────────────────────────────┘
                                │
    1. INGESTION                ▼
    [DeFiHackLabs / Rekt.news] ──► Code-Aware Chunker (600 chars, 100 overlap)
                                │
    2. HYBRID RETRIEVAL         ▼
    [Query] ──┬──► BAAI/bge-small-en-v1.5 (Dense) ──┐
              └──► BM25Okapi Lexical Match (Sparse) ─┴──► Reciprocal Rank Fusion (Top-5)
                                │
    3. REASONING ENGINE         ▼
    [Top-5 Chunks + Invariant] ──► inclusionai/ling-3.0-flash-fin:free (OpenRouter)
                                │
    4. STRUCTURED OUTPUT        ▼
    Pydantic Schema Validation  ──► Verdict, Divergence Point, Residual Risks, Code Patch
                                │
    5. USER TERMINAL            ▼
    Streamlit Web Dashboard     ──► Interactive Lab, Evidence Drawer, Benchmark Suite
```

---

## 📂 Project Structure

```
.
├── data/
│   ├── raw_reports/                 # Authentic post-mortems (DeFiHackLabs & Rekt.news)
│   │   ├── euler_finance.md         # $197M Liquidation/Donation Invariant Omission
│   │   ├── curve_vyper.md           # $73.5M Reentrancy Lock Storage Collision
│   │   ├── cream_finance.md         # $130M Flash Loan Oracle Manipulation
│   │   ├── mango_markets.md         # $114M Illiquid Perp Mark Price Manipulation
│   │   ├── platypus_finance.md      # $8.5M Emergency Withdraw Solvency Omission
│   │   ├── nomad_bridge.md          # $190M Uninitialized Zero Root Validation
│   │   ├── beanstalk_farms.md       # $182M Flash Loan Governance Proposal
│   │   ├── hundred_finance.md       # $7.4M ERC-677 Hook Reentrancy
│   │   └── the_dao.md               # $60M Classical Recursive Reentrancy
│   └── processed_index/             # Cached FAISS index and chunk metadata
├── src/
│   ├── config.py                    # Environment, secrets, and model constants
│   ├── ingestion/
│   │   ├── document_loader.py       # MD, TXT, PDF loader with metadata extraction
│   │   └── chunker.py               # Markdown and Solidity-aware chunker
│   ├── retrieval/
│   │   ├── embedder.py              # BAAI/bge-small-en-v1.5 wrapper
│   │   ├── vector_store.py          # Resilient FAISS store with NumPy fallback
│   │   ├── bm25_search.py           # Lexical keyword searcher
│   │   └── hybrid_retriever.py      # Reciprocal Rank Fusion engine
│   ├── reasoning/
│   │   ├── schemas.py               # Pydantic structured output models
│   │   ├── prompt_templates.py      # Domain-specific counterfactual prompts
│   │   └── openrouter_client.py     # OpenRouter API client with retries
│   ├── evaluation/
│   │   ├── benchmark_data.py        # 5 landmark test cases with ground truths
│   │   └── evaluator.py             # Evaluation runner and metrics calculator
│   └── utils/
│       └── helpers.py               # Badge styling, report generators, JSON export
├── .streamlit/
│   └── config.toml                  # Cyber dark UI styling configuration
├── app.py                           # Streamlit Web Application entrypoint
├── DEPLOYMENT.md                    # Zero-cost cloud deployment guide
├── requirements.txt                 # Pinned lightweight dependencies
├── .env.example                     # Example environment variables
└── README.md
```

---

## ⚡ Quick Start

### 1. Installation
```bash
git clone https://github.com/<YOUR_USERNAME>/counterchain-defi-rag.git
cd counterchain-defi-rag
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and insert your OpenRouter API key:
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=inclusionai/ling-3.0-flash-fin:free
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

### 3. Launch App
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## 🌐 100% Free Cloud Deployment
See **[DEPLOYMENT.md](file:///d:/PY%20Projects/Counterfactual%20Rag%20System%20for%20DeFi%20Exploit%20Analysis/DEPLOYMENT.md)** for a complete 3-minute guide to deploying this application for **100% FREE** with **NO credit cards** on Streamlit Community Cloud or Hugging Face Spaces.
