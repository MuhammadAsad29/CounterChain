import os
import sys
from pathlib import Path
import streamlit as st

# Configure page layout and title
st.set_page_config(
    page_title="CounterChain | DeFi Counterfactual RAG",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add current directory to path for imports
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import (
    OPENROUTER_MODEL,
    EMBEDDING_MODEL_NAME,
    RAW_REPORTS_DIR,
    PROCESSED_INDEX_DIR,
    get_api_key
)
from src.ingestion.document_loader import DocumentLoader
from src.ingestion.chunker import CodeAwareChunker
from src.retrieval.embedder import BGEEmbedder
from src.retrieval.vector_store import FAISSVectorStore
from src.retrieval.hybrid_retriever import HybridRetriever
from src.reasoning.openrouter_client import OpenRouterClient
from src.evaluation.benchmark_data import BENCHMARK_CASES
from src.evaluation.evaluator import BenchmarkEvaluator
from src.utils.helpers import (
    get_verdict_badge_style,
    generate_markdown_report,
    export_json_report
)

# Custom Cyber Dark CSS
st.markdown("""
<style>
    /* Dark Theme Cyber Aesthetic */
    .stApp {
        background-color: #0b0f17;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Header & Branding */
    .brand-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00e676 0%, #00b0ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .brand-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    
    /* Custom Card Style */
    .cyber-card {
        background: #131b26;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    
    /* Verdict Badges */
    .verdict-box {
        padding: 1rem 1.5rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1.3rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin: 1rem 0;
    }

    /* Step Badge */
    .step-badge {
        background: #1e293b;
        color: #00e676;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Cached Pipeline Initialization (Fast Streamlit Cloud Execution)
# -------------------------------------------------------------
@st.cache_resource(show_spinner="Initializing Hybrid RAG Pipeline...")
def initialize_pipeline():
    """Initializes BGE Embedder, loads or builds FAISS index & BM25 store."""
    embedder = BGEEmbedder(model_name=EMBEDDING_MODEL_NAME)
    vector_store = FAISSVectorStore(dimension=384)
    chunker = CodeAwareChunker(chunk_size=600, chunk_overlap=100)

    # 1. Attempt to load from disk
    loaded = vector_store.load(PROCESSED_INDEX_DIR)
    # Check if loaded index has stale or raw .docx names in metadata
    if loaded and any(".docx" in c.metadata.get("protocol", "").lower() for c in vector_store.chunks):
        loaded = False
        vector_store = FAISSVectorStore(dimension=384)
    
    # 2. If index not built yet or stale, ingest raw reports and build index
    if not loaded or len(vector_store.chunks) == 0:
        docs = DocumentLoader.load_directory(RAW_REPORTS_DIR)
        chunks = chunker.chunk_documents(docs)
        if chunks:
            texts = [c.text for c in chunks]
            embeddings = embedder.embed_documents(texts)
            vector_store.add_chunks(chunks, embeddings)
            # Persist to disk for faster future loads
            vector_store.save(PROCESSED_INDEX_DIR)

    retriever = HybridRetriever(vector_store, embedder, vector_store.chunks)
    return embedder, vector_store, chunker, retriever

# Initialize pipeline
embedder, vector_store, chunker, retriever = initialize_pipeline()

# -------------------------------------------------------------
# Sidebar Configuration
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🛡️ **CounterChain Control Panel**")
    st.markdown("*Counterfactual DeFi Exploit Reasoning*")
    st.divider()

    # API Key Management (Secure: Never exposes raw secret key in UI DOM or inputs)
    current_key = get_api_key()
    user_api_key = current_key or ""
    if current_key:
        masked = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else "********"
        st.success(f"🔒 API Key Active (`{masked}`)")
        with st.expander("🔑 Override API Key (Optional)"):
            custom_key = st.text_input(
                "New OpenRouter Key",
                type="password",
                placeholder="sk-or-v1-...",
                help="Enter only if you want to override the environment key."
            )
            if custom_key.strip():
                user_api_key = custom_key.strip()
                os.environ["OPENROUTER_API_KEY"] = user_api_key
    else:
        st.warning("⚠️ No API Key Detected in Secrets/.env")
        entered_key = st.text_input(
            "Enter OpenRouter API Key",
            type="password",
            placeholder="sk-or-v1-...",
            help="Your key is kept in-memory for this session only."
        )
        if entered_key.strip():
            user_api_key = entered_key.strip()
            os.environ["OPENROUTER_API_KEY"] = user_api_key

    # Model Selector
    llm_options = [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "nvidia/nemotron-3.5-lightning:free",
        "openrouter/free"
    ]
    selected_llm = st.selectbox(
        "Primary LLM",
        options=llm_options,
        index=0,
        help="Selected free model. If rate-limited, fallback free models are automatically engaged."
    )
    st.markdown(f"**Embedder**: `{EMBEDDING_MODEL_NAME}`")
    st.markdown(f"**Search**: `Hybrid RRF (Dense BGE + BM25)`")
    st.markdown(f"**Corpus**: `{len(vector_store.chunks)} Chunks Indexed`")
    
    st.divider()
    st.markdown("### 📚 **Official Data Sources**")
    st.caption("✅ **DeFiHackLabs GitHub** (`SunWeb3Sec/DeFiHackLabs`)")
    st.caption("✅ **Rekt.news Incident Archive**")
    st.caption("✅ **PeckShield & OpenZeppelin Audits**")
    
    st.divider()
    if st.button("🔄 Re-Index Knowledge Base", use_container_width=True):
        import shutil
        shutil.rmtree(PROCESSED_INDEX_DIR, ignore_errors=True)
        PROCESSED_INDEX_DIR.mkdir(parents=True, exist_ok=True)
        st.cache_resource.clear()
        st.rerun()

# -------------------------------------------------------------
# Header
# -------------------------------------------------------------
st.markdown('<div class="brand-title">CounterChain: Counterfactual RAG</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="brand-subtitle">Simulate "What-If" Smart Contract Security Interventions Grounded in Official Post-Mortem Documentation</div>',
    unsafe_allow_html=True
)

# App Navigation Tabs
tab_lab, tab_attribution, tab_corpus, tab_benchmark, tab_export = st.tabs([
    "🔬 Counterfactual Lab",
    "🔍 Evidence & Attribution",
    "📁 Exploit Knowledge Base",
    "📊 5-Exploit Benchmark Hub",
    "📥 Audit Report Export"
])

# -------------------------------------------------------------
# TAB 1: Counterfactual Simulation Lab
# -------------------------------------------------------------
with tab_lab:
    st.markdown("#### ⚡ **Simulate Hypothetical Security Intervention**")
    
    col_preset, col_filter = st.columns([3, 1])
    
    with col_preset:
        preset_names = ["-- Select a Benchmark Exploit Preset --"] + [f"{c['protocol']}: {c['query'][:75]}..." for c in BENCHMARK_CASES]
        selected_preset = st.selectbox("Load Verified Exploit Scenario:", preset_names)

    with col_filter:
        available_protos = sorted(list({c.metadata.get("protocol") for c in vector_store.chunks if c.metadata.get("protocol")}))
        protocol_options = ["All Protocols"] + available_protos
        selected_protocol_filter = st.selectbox("Filter Target Protocol:", protocol_options)
        filter_val = None if selected_protocol_filter == "All Protocols" else selected_protocol_filter

    # Determine default query
    default_query = ""
    if selected_preset != "-- Select a Benchmark Exploit Preset --":
        idx = preset_names.index(selected_preset) - 1
        default_query = BENCHMARK_CASES[idx]["query"]

    # Query Input
    user_query = st.text_area(
        "Enter Counterfactual Query (What-if Hypothesis):",
        value=default_query,
        placeholder="e.g. Would the $197M Euler Finance exploit have succeeded if donateToReserves had enforced checkLiquidity(account)?",
        height=100
    )

    # Intervention Shortcut Tags
    st.caption("Common Invariant Interventions:")
    col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
    with col_t1:
        if st.button("🛡️ Reentrancy Guard", use_container_width=True):
            user_query += " What if a nonReentrant mutex lock had been enforced across all pool functions?"
            st.rerun()
    with col_t2:
        if st.button("⏱️ TWAP Oracle", use_container_width=True):
            user_query += " What if a 30-minute decentralized TWAP oracle was used instead of spot pool price?"
            st.rerun()
    with col_t3:
        if st.button("⚖️ Solvency Invariant", use_container_width=True):
            user_query += " What if the function asserted that debt is zero or collateral health ratio is above 1.0?"
            st.rerun()
    with col_t4:
        if st.button("🔒 CEI Pattern", use_container_width=True):
            user_query += " What if state updates occurred before external asset transfers (Checks-Effects-Interactions)?"
            st.rerun()
    with col_t5:
        if st.button("⏳ Snapshot Voting", use_container_width=True):
            user_query += " What if governance voting power was snapshotted at block.number - 1?"
            st.rerun()

    # Simulation Execution
    if st.button("🚀 Run Counterfactual Simulation", type="primary", use_container_width=True):
        if not user_query.strip():
            st.warning("Please enter a counterfactual query or select a preset.")
        else:
            client = OpenRouterClient(api_key=user_api_key or get_api_key(), model=selected_llm)
            
            with st.spinner(f"Retrieving grounded post-mortem evidence & simulating invariants via {selected_llm}..."):
                try:
                    # 1. Retrieve Grounding Evidence
                    retrieved_chunks = retriever.retrieve(
                        query=user_query,
                        top_k=5,
                        protocol_filter=filter_val
                    )

                    # 2. OpenRouter Structured Inference
                    cf_response = client.analyze_counterfactual(
                        query=user_query,
                        retrieved_chunks=retrieved_chunks,
                        protocol_hint=selected_protocol_filter if filter_val else ""
                    )

                    # Save to session state
                    st.session_state["last_query"] = user_query
                    st.session_state["last_protocol"] = selected_protocol_filter
                    st.session_state["last_response"] = cf_response
                    st.session_state["last_retrieved"] = retrieved_chunks

                    st.success("Simulation Complete!")

                except Exception as e:
                    st.error(f"Execution Error: {str(e)}")

    # Display Results if available in session state
    if "last_response" in st.session_state:
        resp = st.session_state["last_response"]
        badge_style = get_verdict_badge_style(resp.verdict.value)

        st.markdown("---")
        st.markdown("### 📋 **Counterfactual Security Verdict**")

        # Visual Verdict Banner
        st.markdown(
            f"""
            <div class="verdict-box" style="background-color: {badge_style['bg']}; border: 1.5px solid {badge_style['border']}; color: {badge_style['color']};">
                <span>{badge_style['icon']}</span>
                <span>{badge_style['label']}</span>
                <span style="margin-left: auto; font-size: 0.95rem; color: #94a3b8;">Confidence: {resp.confidence_score * 100:.1f}%</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.info(f"**Executive Summary**: {resp.executive_summary}")

        # Causal Divergence & Trace
        col_res1, col_res2 = st.columns([3, 2])

        with col_res1:
            st.markdown("#### 🔄 **Execution Divergence Point**")
            st.markdown(f"> ⚡ `{resp.divergence_point}`")

            st.markdown("#### ⛓️ **Step-by-Step Causal State Trace**")
            for idx, step in enumerate(resp.causal_reasoning_steps, 1):
                st.markdown(f'<span class="step-badge">STEP {idx}</span> {step}', unsafe_allow_html=True)

        with col_res2:
            st.markdown("#### ⚠️ **Residual Risks & Bypass Vectors**")
            if resp.residual_risks:
                for r in resp.residual_risks:
                    st.warning(f"**Risk**: {r}")
            else:
                st.success("No critical residual attack vectors detected.")

            st.markdown("#### 💻 **Recommended Solidity Patch**")
            st.code(resp.recommended_code_patch, language="solidity")

# -------------------------------------------------------------
# TAB 2: Evidence & Attribution
# -------------------------------------------------------------
with tab_attribution:
    st.markdown("#### 🔍 **Retrieved Grounding Evidence (Top-5 Chunks)**")
    st.caption("Fused via Reciprocal Rank Fusion (BGE Dense Embeddings + BM25 Lexical Matching)")

    if "last_retrieved" in st.session_state and st.session_state["last_retrieved"]:
        chunks = st.session_state["last_retrieved"]
        for c in chunks:
            with st.expander(f"Rank #{c['rank']}: {c['protocol']} — {c['section']} (Score: {c['rrf_score']})", expanded=(c['rank'] <= 2)):
                st.markdown(f"**Source Document**: `{c['sources']}` | **Vulnerability Category**: `{c['vulnerability_category']}` | **Reported Loss**: `{c['loss_amount']}`")
                st.markdown("```text\n" + c['text'] + "\n```")
                col_m1, col_m2 = st.columns(2)
                col_m1.caption(f"Dense Rank: {c.get('dense_rank', 'N/A')}")
                col_m2.caption(f"BM25 Rank: {c.get('sparse_rank', 'N/A')}")
    else:
        st.info("Run a counterfactual simulation in the Lab tab to view retrieved grounding evidence.")

# -------------------------------------------------------------
# TAB 3: Exploit Knowledge Base
# -------------------------------------------------------------
with tab_corpus:
    st.markdown("#### 📁 **Indexed DeFi Exploit Documentation**")
    st.caption("All reports sourced from verified GitHub repositories (DeFiHackLabs), Rekt.news, and top audit firms.")

    raw_docs = DocumentLoader.load_directory(RAW_REPORTS_DIR)
    
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        st.markdown(f"**Total Verified Reports**: `{len(raw_docs)}` | **Total Semantic Chunks**: `{len(vector_store.chunks)}`")
        
        # Display list of documents
        for doc in raw_docs:
            meta = doc.metadata
            with st.expander(f"📄 {meta.get('protocol', 'Unknown')} ({meta.get('loss_amount', 'N/A')})"):
                st.markdown(f"- **Vulnerability Category**: `{meta.get('vulnerability_category', 'N/A')}`")
                st.markdown(f"- **Incident Date**: `{meta.get('incident_date', 'N/A')}`")
                st.markdown(f"- **Official Sources**: `{meta.get('sources', 'N/A')}`")
                st.text_area("Post-Mortem Content Preview", doc.content[:1000] + "...", height=150, key=f"prev_{doc.doc_id}")

    with col_c2:
        st.markdown("#### 📤 **Upload New Post-Mortem**")
        st.caption("Add custom Markdown, TXT, or PDF audit reports to the live index.")
        uploaded_file = st.file_uploader("Upload Audit Document", type=["md", "txt", "pdf", "docx"])
        if uploaded_file:
            if st.button("➕ Ingest & Re-Index", use_container_width=True):
                doc = DocumentLoader.load_from_upload(uploaded_file.name, uploaded_file.read())
                if doc:
                    # Save to raw_reports
                    target_path = RAW_REPORTS_DIR / uploaded_file.name
                    target_path.write_bytes(uploaded_file.getvalue())
                    st.cache_resource.clear()
                    st.success(f"Successfully ingested {uploaded_file.name}! Reloading...")
                    st.rerun()

# -------------------------------------------------------------
# TAB 4: 5-Exploit Benchmark Hub
# -------------------------------------------------------------
with tab_benchmark:
    st.markdown("#### 📊 **5-Exploit Benchmark Evaluation Suite**")
    st.caption("Automated validation of CounterChain against documented ground-truth verdicts.")

    col_b1, col_b2 = st.columns([3, 1])
    with col_b1:
        st.markdown("Evaluates precision on: Euler Finance, Curve Vyper Reentrancy, Cream Finance, Platypus Finance, and a Control Case.")
    with col_b2:
        run_bench = st.button("▶️ Run Automated Benchmark", type="primary", use_container_width=True)

    if run_bench:
        client = OpenRouterClient(api_key=user_api_key or get_api_key(), model=selected_llm)
        evaluator = BenchmarkEvaluator(retriever, client)
        
        with st.spinner(f"Running benchmark exploit cases through CounterChain via {selected_llm}..."):
            summary = evaluator.run_all_benchmarks()
            st.session_state["benchmark_summary"] = summary

    if "benchmark_summary" in st.session_state:
        b_sum = st.session_state["benchmark_summary"]
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Verdict Concordance", f"{b_sum['verdict_accuracy_pct']}%", delta="Target: >=80%")
        col_m2.metric("Retrieval Precision @ 5", f"{b_sum['retrieval_precision_pct']}%", delta="100% Target")
        col_m3.metric("Benchmark Cases", f"{b_sum['total_cases']}", "5 Verified Exploits")

        st.markdown("---")
        st.markdown("##### 📝 **Detailed Case Breakdown**")
        
        for case in b_sum["cases_evaluated"]:
            match_icon = "✅ MATCH" if case["verdict_match"] else "❌ MISMATCH"
            with st.expander(f"{case['case_id']}: {case['protocol']} — {match_icon}"):
                col_e1, col_e2 = st.columns(2)
                col_e1.markdown(f"**Expected Ground Truth**: `{case['ground_truth_verdict']}`")
                col_e2.markdown(f"**CounterChain Verdict**: `{case['model_verdict']}`")
                st.markdown(f"**Executive Finding**: {case['executive_summary']}")
                st.markdown(f"**Execution Divergence Point**: `{case['divergence_point']}`")
                st.code(case['recommended_code_patch'], language="solidity")

# -------------------------------------------------------------
# TAB 5: Audit Report Export
# -------------------------------------------------------------
with tab_export:
    st.markdown("#### 📥 **Export Security Audit Report**")
    st.caption("Download the complete counterfactual assessment formatted for audit presentations or security disclosures.")

    if "last_response" in st.session_state:
        l_query = st.session_state.get("last_query", "DeFi Counterfactual Invariant Query")
        l_proto = st.session_state.get("last_protocol", "DeFi Protocol")
        l_resp = st.session_state.get("last_response")
        l_ret = st.session_state.get("last_retrieved", [])

        md_report = generate_markdown_report(l_query, l_proto, l_resp, l_ret)
        json_report = export_json_report(l_query, l_proto, l_resp, l_ret)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "📄 Download Markdown Audit Report",
                data=md_report,
                file_name=f"CounterChain_Report_{l_proto.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col_d2:
            st.download_button(
                "💾 Download JSON Machine-Readable Report",
                data=json_report,
                file_name=f"CounterChain_Report_{l_proto.replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True
            )

        st.markdown("##### Report Preview:")
        st.markdown(md_report)
    else:
        st.info("Perform a simulation in the Lab tab to generate an exportable report.")
