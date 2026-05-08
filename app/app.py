import streamlit as st
import time
from agents import run_baseline, run_single_agent, run_multi_agent
from config import ACTIVE_MODEL

st.set_page_config(page_title="FinTech AI Agent", layout="wide")
st.title("🏦 FinTech AI Agent - Stock Analysis")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    architecture = st.selectbox(
        "Architecture",
        ["Baseline", "Single Agent", "Multi Agent"],
        index=2
    )

    st.markdown("---")
    st.markdown(f"**Model:** {ACTIVE_MODEL}")

    st.markdown("---")
    st.markdown("### 📊 Available Tools")
    st.markdown("""
    - 📈 Price Performance
    - 💼 Company Overview
    - 📰 News Sentiment
    - 🏢 Sector Lookup
    - 🔍 SQL Query
    - 📊 Market Status
    - 🔥 Top Movers
    """)

    st.markdown("---")
    st.markdown("### 💡 Examples")
    if st.button("What is Apple's P/E ratio?"):
        st.session_state.example = "What is Apple's P/E ratio?"
    if st.button("Compare AAPL, MSFT, NVDA"):
        st.session_state.example = "Compare the P/E ratios of AAPL, MSFT, and NVDA"
    if st.button("Top energy stocks"):
        st.session_state.example = "Which energy stocks had the best 6-month performance?"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and "metadata" in msg:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("⏱️ Time", f"{msg['metadata'].get('time', 0):.1f}s")
            with col2:
                st.metric("🔧 Tools", msg['metadata'].get('tool_count', 0))
            with col3:
                st.metric("🏗️ Arch", msg['metadata'].get('architecture', 'N/A'))

            if msg['metadata'].get('tools'):
                with st.expander("🔧 Tools Used"):
                    for tool in msg['metadata']['tools']:
                        st.code(tool)

# Handle example button clicks
if "example" in st.session_state:
    prompt = st.session_state.example
    del st.session_state.example
else:
    prompt = st.chat_input("Ask about stocks...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"🤖 {architecture} is thinking..."):
            start_time = time.time()

            try:
                if architecture == "Baseline":
                    result = run_baseline(prompt, verbose=False)
                    answer = result.answer
                    tools = []

                elif architecture == "Single Agent":
                    result = run_single_agent(prompt, verbose=False)
                    answer = result.answer
                    tools = result.tools_called

                else:  # Multi Agent
                    result = run_multi_agent(prompt, verbose=False)
                    answer = result["final_answer"]
                    tools = [t for r in result["agent_results"] for t in r.tools_called]

                elapsed = time.time() - start_time

                st.markdown(answer)

                # Display metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⏱️ Time", f"{elapsed:.1f}s")
                with col2:
                    st.metric("🔧 Tools", len(tools))
                with col3:
                    st.metric("🏗️ Arch", architecture)

                if tools:
                    with st.expander("🔧 Tools Used"):
                        for tool in tools:
                            st.code(tool)

                # Save to session
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "metadata": {
                        "time": elapsed,
                        "tools": tools,
                        "tool_count": len(tools),
                        "architecture": architecture
                    }
                })

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.exception(e)
