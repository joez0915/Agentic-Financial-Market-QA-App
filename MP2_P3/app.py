import streamlit as st
import os

from agents.head_agent import Head_Agent

# Page setup
st.set_page_config(page_title="Mini Project 3 - Multi-Agent Chatbot")
st.title("Mini Project Part 3: Multi-Agent Chatbot")

# Sidebar: keys + config
with st.sidebar:
    st.header("Configuration")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    pinecone_api_key = st.text_input("Pinecone API Key", type="password")

    # Keep your existing constants
    INDEX_NAME = "mini2"
    NAMESPACE = "ns2500"

    st.markdown(f"**Index:** `{INDEX_NAME}`")
    st.markdown(f"**Namespace:** `{NAMESPACE}`")

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

if not openai_api_key or not pinecone_api_key:
    st.warning("Please enter both OpenAI and Pinecone API Keys in the sidebar to continue.")
    st.stop()

os.environ["OPENAI_API_KEY"] = openai_api_key
os.environ["PINECONE_API_KEY"] = pinecone_api_key


def _truncate(s: str, n: int = 350) -> str:
    s = "" if s is None else str(s)
    return s if len(s) <= n else s[:n] + "..."


@st.cache_resource
def get_head_agent(openai_key: str, pinecone_key: str, index_name: str, namespace: str) -> Head_Agent:
    return Head_Agent(openai_key, pinecone_key, index_name, namespace=namespace)


try:
    head = get_head_agent(openai_api_key, pinecone_api_key, INDEX_NAME, NAMESPACE)
    st.sidebar.success("Connected to OpenAI + Pinecone!")
except Exception as e:
    st.error(f"Failed to initialize agents: {e}")
    st.stop()

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4.1-nano"

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input("Ask a question about the indexed content..."):
    # 1) show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) run controller pipeline
    # Pass history WITHOUT the current user message (so rewrite agent sees prior context)
    result = head.handle(prompt, history=st.session_state.messages[:-1], k=5)

    with st.chat_message("assistant"):
        # "Brain Process" — show different message for greeting/obnoxious vs normal QA
        if result.get("is_greeting"):
            st.info("**Brain Process**: Greeting detected — replied with a short welcome.")
        elif result.get("is_obnoxious"):
            st.info("**Brain Process**: Query was flagged as impolite — asked user to rephrase.")
        else:
            st.info(f"**Brain Process**: I rephrased your question to: '*{result.get('rewritten_query', '')}*'")

        # retrieved docs expander
        with st.expander("Retrieved Context"):
            docs = result.get("docs", []) or []
            if not docs:
                st.caption("No documents retrieved.")
            else:
                for i, d in enumerate(docs, 1):
                    # d is RetrievedDoc (text, metadata)
                    page = d.metadata.get("page_number", d.metadata.get("page", "N/A"))
                    st.markdown(f"**Chunk {i} (Page {page})**")
                    st.caption(_truncate(d.text, 600))

        # 3) stream or print final answer
        if result.get("final_stream") is None:
            response_text = result.get("final_text", "")
            st.markdown(response_text)
        else:
            response_text = st.write_stream(result["final_stream"])

    # 4) persist assistant reply to history
    st.session_state.messages.append({"role": "assistant", "content": response_text})
