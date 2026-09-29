# 🚀 100% Free Zero-Friction Cloud Deployment Guide

This system is specifically architected so that **ANYONE can deploy it completely for FREE** in under 3 minutes with:
- ❌ **NO Credit Card** required
- ❌ **NO Docker setup** required
- ❌ **NO Paid Cloud Accounts** (No AWS, No GCP, No Azure bills)
- ✅ **100% Free Hosting** on Streamlit Community Cloud or Hugging Face Spaces

---

## Option 1: Streamlit Community Cloud (Recommended — 3 Minutes)

Streamlit Community Cloud gives you free hosting directly connected to your GitHub repository.

### Step 1: Push your Code to GitHub
1. Create a free repository on [GitHub](https://github.com/new) (e.g. `counterchain-defi-rag`).
2. Push your project code to GitHub:
```bash
git init
git add .
git commit -m "feat: CounterChain DeFi Exploit RAG System"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/counterchain-defi-rag.git
git push -u origin main
```

### Step 2: Open Streamlit Community Cloud
1. Go to **[share.streamlit.io](https://share.streamlit.io)** and log in with your GitHub account (No credit card needed).
2. Click **"New App"** (or **"Create app"**).
3. Select your repository: `<YOUR_USERNAME>/counterchain-defi-rag`.
4. Branch: `main`.
5. Main file path: `app.py`.

### Step 3: Add Your Free OpenRouter Key to Secrets
1. Before clicking Deploy, click **"Advanced settings..."** (or expand the **Secrets** section).
2. In the Secrets text box, paste your OpenRouter key:
```toml
OPENROUTER_API_KEY = "your_openrouter_api_key_here"
OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
```
3. Click **"Save"**.

### Step 4: Click "Deploy!"
- Streamlit Community Cloud will automatically read `requirements.txt`, install the lightweight CPU-friendly packages, download the 133MB `bge-small-en-v1.5` model, and launch your live app!
- You will receive a permanent public URL (e.g. `https://counterchain-defi.streamlit.app`) that you can share with evaluators, professors, or team members.

---

## Option 2: Running Locally on Any Workstation

If you or your examiners want to run the project locally on Windows, Mac, or Linux:

1. Clone or open the project folder:
```bash
cd "Counterfactual Rag System for DeFi Exploit Analysis"
```

2. (Optional) Create a virtual environment:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate
```

3. Install requirements:
```bash
pip install -r requirements.txt
```

4. Launch the Streamlit application:
```bash
streamlit run app.py
```
Your browser will automatically open `http://localhost:8501`.

---

## Option 3: Hugging Face Spaces (Alternative 100% Free Option)

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and click **"Create new Space"**.
2. Select **Streamlit** SDK and choose the **Free CPU Basic (16 GB RAM)** tier.
3. Push the repository files to Hugging Face.
4. Under **Settings -> Variables and secrets**, add `OPENROUTER_API_KEY` as a secret.
5. Your app goes live automatically!

---

## Why This Implementation Guarantees Zero Deployment Headaches:
1. **Lightweight CPU Embeddings**: `BAAI/bge-small-en-v1.5` uses only ~133MB of RAM, safely under free cloud limits (1GB on Streamlit Cloud, 16GB on Hugging Face).
2. **Self-Contained Vector Store**: FAISS + pure-Numpy fallback means the app never crashes even if a platform has binary library quirks.
3. **No External Database Servers**: Exploit reports and vector indices reside directly within the application repository.
4. **Secret Fallback Chain**: Automatically checks `st.secrets` first, then `.env`, then UI input in the sidebar.
