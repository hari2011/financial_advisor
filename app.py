"""
FinanceGPT - AI Personal Financial Advisor
==========================================
A local, privacy-first financial advisor powered by Llama 3.1 8B.
All processing happens on your machine - no data leaves your computer.
"""
import sys
import os
import time
import logging

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────── Logging Setup ────────────────────────
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "financegpt.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("financegpt.app")

import streamlit as st
from agents.router import route_query, list_agents, AGENT_REGISTRY
from config import AGENTS, AGENT_ICONS

# ──────────────────────── Page Config ────────────────────────
st.set_page_config(
    page_title="FinanceGPT - AI Financial Advisor",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────── Load CSS ────────────────────────
css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ──────────────────────── Session State ────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_agent" not in st.session_state:
    st.session_state.selected_agent = "auto"
if "llm_loaded" not in st.session_state:
    st.session_state.llm_loaded = False

# ──────────────────────── Sidebar ────────────────────────
with st.sidebar:
    st.markdown("## 💹 FinanceGPT")
    st.markdown("---")

    # LLM Status
    if st.session_state.llm_loaded:
        st.markdown('<span class="status-dot online"></span> **LLM Ready**', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-dot loading"></span> **LLM: Will load on first query**', unsafe_allow_html=True)

    st.markdown("---")

    # Agent Selection
    st.markdown("### 🤖 Select Agent")
    st.caption("Choose an agent or let auto-routing decide")

    agent_options = {"auto": "🔄 Auto-Route (Smart Selection)"}
    for key, name in AGENTS.items():
        icon = AGENT_ICONS.get(key, "🤖")
        agent_options[key] = f"{icon} {name}"

    selected = st.radio(
        "Agent",
        options=list(agent_options.keys()),
        format_func=lambda x: agent_options[x],
        index=0,
        label_visibility="collapsed",
    )
    st.session_state.selected_agent = selected

    if selected != "auto":
        agent = AGENT_REGISTRY[selected]
        st.info(f"**{agent.name}**\n\n{agent.description}")

    st.markdown("---")

    # Quick Actions
    st.markdown("### ⚡ Quick Actions")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Markets", use_container_width=True):
            st.session_state.quick_query = "Give me an overview of Nifty 50, Sensex, and Bank Nifty today"
        if st.button("💰 Budget", use_container_width=True):
            st.session_state.quick_query = "Help me create a budget for a monthly income of ₹75,000"
        if st.button("🏠 EMI Calc", use_container_width=True):
            st.session_state.quick_query = "Calculate EMI for a home loan of ₹50 lakh at 8.5% for 20 years"
        if st.button("📊 MF Picks", use_container_width=True):
            st.session_state.quick_query = "Recommend the best mutual funds for SIP in 2025 across large, mid, and small cap"
    with col2:
        if st.button("₿ Crypto", use_container_width=True):
            st.session_state.quick_query = "What's the current price of Bitcoin and Ethereum? How are they taxed in India?"
        if st.button("🏖️ Retire", use_container_width=True):
            st.session_state.quick_query = "I spend ₹50,000/month. How much SIP do I need to retire in 25 years?"
        if st.button("🏛️ Tax", use_container_width=True):
            st.session_state.quick_query = "Compare new vs old tax regime for annual income of ₹12 lakh"
        if st.button("🛡️ Insurance", use_container_width=True):
            st.session_state.quick_query = "I earn ₹15 lakh/year with 2 dependents. What insurance coverage do I need?"

    st.markdown("---")

    # Clear Chat
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption("🔒 100% Local & Private")
    st.caption("Powered by Llama 3.1 8B")
    st.caption("No data leaves your machine")

# ──────────────────────── Main Chat Area ────────────────────────

# Display welcome message if no messages
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-container">
        <h1>💹 FinanceGPT</h1>
        <p>Your AI-Powered Personal Financial Advisor</p>
        <br>
        <p style="font-size: 0.95em; color: #9ca3af;">
            Ask me anything about Indian stocks (NSE/BSE), mutual funds, SIP planning, taxes (new/old regime),
            loans, budgeting, crypto, insurance, or retirement planning. I have 10 specialized agents
            ready to help, with real-time market data and web search capabilities.
            All amounts default to ₹ (Indian Rupees) in Lakhs and Crores.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Suggested prompts
    st.markdown("#### 💡 Try asking:")
    suggestions = [
        "Analyze Reliance Industries stock - fundamentals and outlook",
        "I earn ₹1 lakh/month. Create a detailed budget with SIP recommendations.",
        "Compare SIP returns: ₹10,000/month for 10, 20, and 30 years at 12%",
        "Best ELSS mutual funds for tax saving under Section 80C",
        "Calculate home loan EMI for ₹40 lakh at 8.5% for 20 years with tax benefits",
        "New vs Old tax regime - which is better for ₹15 lakh salary?",
    ]

    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(f"💬 {suggestion}", key=f"sug_{i}", use_container_width=True):
                st.session_state.quick_query = suggestion

# Display chat messages
for msg in st.session_state.messages:
    avatar = "💹" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        # Show agent badge for assistant messages
        if msg["role"] == "assistant" and "agent" in msg:
            agent_key = msg["agent"]
            icon = AGENT_ICONS.get(agent_key, "🤖")
            name = AGENTS.get(agent_key, "General Advisor")
            badge_class = agent_key.split("_")[0]
            st.markdown(
                f'<span class="agent-badge {badge_class}">{icon} {name}</span>',
                unsafe_allow_html=True,
            )
        st.markdown(msg["content"])

# Handle quick query buttons
if "quick_query" in st.session_state:
    query = st.session_state.pop("quick_query")
    st.session_state.messages.append({"role": "user", "content": query})
    st.rerun()

# Chat input
if prompt := st.chat_input("Ask your financial question..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    logger.info(f"User query: {prompt[:150]}")

    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Route to appropriate agent
    manual = None if st.session_state.selected_agent == "auto" else st.session_state.selected_agent
    agent_key, agent = route_query(prompt, manual)
    icon = AGENT_ICONS.get(agent_key, "🤖")
    name = AGENTS.get(agent_key, "General Advisor")
    logger.info(f"Routed to: {agent_key} ({name})")

    with st.chat_message("assistant", avatar="💹"):
        badge_class = agent_key.split("_")[0]
        st.markdown(
            f'<span class="agent-badge {badge_class}">{icon} {name}</span>',
            unsafe_allow_html=True,
        )

        status_container = st.status(f"🔍 {name} is working...", expanded=True)
        response = None
        error_msg = None

        with status_container:
            try:
                # Step 1: Initialize LLM if needed
                from llm.engine import llm as llm_engine
                if not llm_engine._initialized:
                    st.write("⏳ Loading LLM model into memory (first time only)...")
                    logger.info("Initializing LLM for the first time...")
                    t0 = time.time()
                    llm_engine.initialize()
                    st.session_state.llm_loaded = True
                    st.write(f"✅ LLM loaded in {time.time()-t0:.1f}s")

                # Step 2: Gather context
                st.write("📊 Gathering market data and context...")
                t1 = time.time()
                context = agent.gather_context(prompt)
                ctx_time = time.time() - t1
                ctx_len = len(context) if context else 0
                st.write(f"✅ Context ready ({ctx_len:,} chars in {ctx_time:.1f}s)")
                logger.info(f"Context gathered: {ctx_len} chars in {ctx_time:.1f}s")

                # Step 3: Generate response
                st.write("🧠 Generating AI response...")
                t2 = time.time()
                response = llm_engine.generate(agent.system_prompt, prompt, context)
                gen_time = time.time() - t2
                total_time = time.time() - t1
                st.write(f"✅ Response generated in {gen_time:.1f}s (total: {total_time:.1f}s)")
                logger.info(f"Response generated: {len(response)} chars in {gen_time:.1f}s")

            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                logger.error(f"ERROR processing query: {e}\n{error_detail}")
                st.write(f"❌ Error: {e}")
                error_msg = (
                    f"⚠️ **Error:** {str(e)}\n\n"
                    f"Please check the logs at `logs/financegpt.log` for details.\n\n"
                    f"If the model hasn't been downloaded, run:\n"
                    f"```\ncd financial_advisor && python setup_model.py\n```"
                )

        # Update status label
        if response:
            status_container.update(label=f"✅ {name} — completed", state="complete", expanded=False)
            st.markdown(response)
        else:
            status_container.update(label=f"❌ {name} — failed", state="error", expanded=True)
            st.markdown(error_msg or "⚠️ No response generated. Please try again.")

    # Save assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": response or error_msg or "No response generated.",
        "agent": agent_key,
    })
