import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Data Assistant", page_icon="🤖", layout="wide")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("AI Data Assistant")
st.caption("Ask questions about customers, products, orders, and employees.")

with st.sidebar:
    st.header("Prompt ideas")
    sample_prompts = [
        "Show all customers in Delhi",
        "Which employees work in Sales?",
        "What is the most expensive product?",
        "List all orders for Aditi Sharma",
        "Who is the top-selling product?",
    ]
    for sample in sample_prompts:
        if st.button(sample, key=f"prompt_{sample}"):
            st.session_state.current_prompt = sample

    st.markdown("---")
    st.subheader("Last generated SQL")
    if st.session_state.chat_history:
        latest_sql = next((msg.get("sql") for msg in reversed(st.session_state.chat_history) if msg.get("sql")), "No SQL generated yet.")
        st.code(latest_sql, language="sql")
    else:
        st.write("No SQL generated yet.")

    st.markdown("---")
    st.markdown("**Expected answer style:** short, clear, fact-based, and based on the database records.")

if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = ""

prompt = st.text_area(
    "Your question",
    value=st.session_state.current_prompt,
    placeholder="Example: Show all customers from Delhi and list their contact details.",
    height=120,
)

col1, col2 = st.columns([1, 1])
with col1:
    ask_clicked = st.button("Generate answer", use_container_width=True)
with col2:
    clear_clicked = st.button("Clear chat", use_container_width=True)

if clear_clicked:
    st.session_state.chat_history = []
    st.session_state.current_prompt = ""
    st.rerun()

if ask_clicked and prompt.strip():
    user_message = prompt.strip()
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/ask",
            json={"question": user_message},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()

        st.session_state.chat_history.append({
            "role": "user",
            "content": user_message,
            "sql": payload.get("sql", ""),
        })
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": payload.get("answer", "No answer returned."),
            "sql": payload.get("sql", ""),
            "summary": payload.get("summary", ""),
        })
        st.session_state.current_prompt = ""
        st.rerun()
    except Exception as exc:
        st.error(f"Unable to reach the backend API: {exc}")

st.markdown("---")

if st.session_state.chat_history:
    for item in st.session_state.chat_history:
        if item["role"] == "user":
            with st.chat_message("user"):
                st.markdown(item["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(item["content"])
                if item.get("summary"):
                    st.caption(item["summary"])
                if item.get("sql"):
                    with st.expander("View generated SQL"):
                        st.code(item["sql"], language="sql")
else:
    with st.chat_message("assistant"):
        st.markdown("Ask a question to begin the conversation.")

st.markdown("---")
st.subheader("Supported question types")
col1, col2 = st.columns(2)
with col1:
    st.write("- Customer questions")
    st.write("- Product questions")
    st.write("- Order questions")
with col2:
    st.write("- Employee questions")
    st.write("- City or department filters")
