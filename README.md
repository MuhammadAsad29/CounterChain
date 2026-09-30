# CounterChain: A Counterfactual RAG System for DeFi Exploit Analysis

[![Streamlit Ready](https://img.shields.io/badge/Streamlit-Ready-FF4B4B?style=flat&logo=streamlit)](https://streamlit.io)
[![Model](https://img.shields.io/badge/LLM-NVIDIA%20Nemotron%20%7C%20OpenRouter%20Free-blue)](https://openrouter.ai)
[![Embeddings](https://img.shields.io/badge/Embeddings-BAAI%2Fbge--small--en--v1.5-green)](https://huggingface.co/BAAI/bge-small-en-v1.5)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)

**CounterChain** is a domain-specific Retrieval-Augmented Generation (RAG) system engineered to perform structured counterfactual reasoning over historical Decentralized Finance (DeFi) exploits.

🔗 Live Deployment: https://counterchain.streamlit.app/

Instead of merely retrieving historical post-mortems, CounterChain evaluates hypothetical security interventions:
> *"Would the $197M Euler Finance exploit have succeeded if donateToReserves had strictly enforced checkLiquidity on the donor account?"*

---

## 🎯 Key Capabilities

- **Counterfactual Causality Engine**: Contrasts the historical attack trace against the hypothetical counterfactual branch, pinning down the exact point of execution divergence.
- **Structured Security Verdicts**: Generates standardized classifications:
  - 🛡️ `PREVENTED`: Transaction reverts at divergence point (e.g., require assertion failure).
  - ⚠️ `PARTIALLY_MITIGATED`: Exploit slowed down, limited in capital extraction, or higher complexity.
  - 🚨 `VULNERABILITY_PERSISTS`: The patch fails to address the root exploit mechanism.
  - 🔄 `SHIFTED_ATTACK_VECTOR`: Patch introduces a new bypass or attack surface.
  - ❓ `INCONCLUSIVE`: Insufficient post-mortem telemetry to prove invariant state.
- **Hybrid Search (Dense BGE + Sparse BM25)**: Uses **`BAAI/bge-small-en-v1.5`** alongside **BM25Okapi** fused via **Reciprocal Rank Fusion (RRF)** to accurately retrieve both conceptual vectors and exact Solidity function signatures (`donateToReserves`, `emergencyWithdraw`, `executeDecreaseOrder`).
- **100% Verified Official Dataset**: Sourced exclusively from **DeFiHackLabs GitHub (`SunWeb3Sec/DeFiHackLabs`)**, **Rekt.news Incident Archive**, and top security audit firms (Sherlock, PeckShield, OpenZeppelin, Trail of Bits).
- **Automated Exploit Benchmark Hub**: Pre-configured evaluation suite measuring retrieval recall, verdict concordance, and execution latency against documented ground-truth audit verdicts.
- **Production-Ready & Cloud Deployable**: Zero-dependency on paid APIs or GPU hardware; executes smoothly on free tiers (Streamlit Community Cloud / Hugging Face Spaces) under 1GB RAM.

---

## 🧠 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       COUNTERCHAIN PIPELINE                 │
└─────────────────────────────────────────────────────────────┘
                                │
    1. INGESTION                ▼
    [DeFiHackLabs / Sherlock] ──► Code-Aware Chunker (600 chars, 100 overlap)
                                │
    2. HYBRID RETRIEVAL         ▼
    [Query] ──┬──► BAAI/bge-small-en-v1.5 (Dense) ──┐
              └──► BM25Okapi Lexical Match (Sparse) ─┴──► Reciprocal Rank Fusion (Top-5)
                                │
    3. REASONING ENGINE         ▼
    [Top-5 Chunks + Invariant] ──► NVIDIA Nemotron / OpenRouter Free LLM
                                │
    4. RESILIENT JSON PARSER    ▼
    Multi-stage Extraction     ──► json.loads -> ast.literal_eval -> Regex Fallback
                                │
    5. STRUCTURED OUTPUT        ▼
    Pydantic Schema Validation ──► Verdict, Divergence Point, Residual Risks, Code Patch
                                │
    6. USER TERMINAL            ▼
    Streamlit Web Dashboard    ──► Counterfactual Lab, Evidence Drawer, Benchmark Hub
```

---

## 📂 Verified Dataset Inventory (16 Reports)

All dataset files in `data/raw_reports/` are authenticated post-mortems and security audit reports:

| Report File | Format | Target Protocol / Ecosystem | Loss / Impact | Primary Root Cause Category |
| :--- | :---: | :--- | :--- | :--- |
| `euler_finance.md` | `.md` | Euler Finance | $197,000,000 | Liquidation / Donation Solvency Omission |
| `cream_finance.md` | `.md` | Cream Finance | $130,000,000 | Flash Loan Spot Oracle Manipulation |
| `curve_vyper.md` | `.md` | Curve Finance / Vyper | $73,500,000 | Compiler Storage Slot Mutex Lock Collision |
| `mango_markets.md` | `.md` | Mango Markets (Solana) | $114,000,000 | Illiquid Perpetual Mark Price Manipulation |
| `nomad_bridge.md` | `.md` | Nomad Bridge | $190,000,000 | Uninitialized 0x00 Message Root Bypass |
| `beanstalk_farms.md` | `.md` | Beanstalk Farms | $182,000,000 | Flash Loan Emergency Governance Hijack |
| `wormhole_bridge.md` | `.md` | Wormhole Bridge (Solana) | $326,000,000 | Deprecated `verify_signatures` Instruction Spoofing |
| `harvest_finance.md` | `.md` | Harvest Finance | $33,800,000 | Single-block Curve Pool Price Manipulation |
| `hundred_finance.md` | `.md` | Hundred Finance (Optimism) | $7,400,000 | Compound v2 Fork ERC-677 Reentrancy Hook |
| `platypus_finance.md` | `.md` | Platypus Finance | $8,500,000 | `emergencyWithdraw` Solvency Assertion Missing |
| `saddle_finance.md` | `.md` | Saddle Finance | $11,000,000 | MetaSwap Virtual Price Calculation Flaw |
| `the_dao.md` | `.md` | The DAO | $60,000,000 | Classical Fallback Function Recursive Reentrancy |
| `GMX EXCHANGE HACK EXPLAINED.docx` | `.docx` | GMX Exchange (Arbitrum) | $42,000,000 | Price Impact & GLP Reentrant Short Leverage |
| `THE SHERLOCK WEB3 REPORT Q1.docx`| `.docx` | Sherlock Web3 Security | Multi-Protocol | Q1 2024 Audit Cases (Resolv, Venus, YieldBlox) |
| `What is a Flashloan Attack.docx` | `.docx` | Sherlock Research | Methodology | Cross-Block Flash Loan Attack Invariant Analysis |
| `CROSS-CHAIN SECURITY IN 2026.docx`| `.docx` | Sherlock Research | Cross-Chain | Bridge Verification & Cryptographic Invariants |

---

## 📊 5-Exploit Benchmark Evaluation Suite

CounterChain includes an automated evaluation hub to validate precision against documented ground-truth verdicts:

| Case ID | Protocol Target | Verified Invariant Question | Ground Truth | Expected Verdict |
| :---: | :--- | :--- | :---: | :---: |
| **BENCH-01** | Euler Finance | `donateToReserves` enforced `checkLiquidity` | Proven Audit Fix | 🛡️ `PREVENTED` |
| **BENCH-02** | Curve Finance | Compiled with Vyper 0.3.1 storage-slot fix | Compiler Release | 🛡️ `PREVENTED` |
| **BENCH-03** | Cream Finance | 30-min Chainlink TWAP oracle instead of spot | Security Advisory | 🛡️ `PREVENTED` |
| **BENCH-04** | Platypus Finance | `emergencyWithdraw` required `debtOf == 0` | Patch PR #14 | 🛡️ `PREVENTED` |
| **BENCH-05** | Cream (Control) | Capping flash loan size to $50M without TWAP | Control Test | 🚨 `VULNERABILITY_PERSISTS` |
| **BENCH-06** | GMX V1 | `disableLeverage()` before profit ETH transfer | CEI Rule | 🛡️ `PREVENTED` |

---

## ⚡ Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/MuhammadAsad29/CounterChain.git
cd CounterChain
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Key
Create a `.env` file (or set via Streamlit secrets):
```env
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key_here
OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

### 4. Run Application
```bash
streamlit run app.py
```
Access the application at `http://localhost:8501`.

---

## 🌐 100% Free Cloud Deployment

Detailed step-by-step instructions for deploying to **Streamlit Community Cloud** with zero infrastructure costs and no credit cards are available in **[DEPLOYMENT.md](DEPLOYMENT.md)**.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.
