"""Streamlit chat UI with a live agent reasoning trace. Run: streamlit run src/app.py"""
import io
import sys
import streamlit as st

from src.agent import build_agent


st.set_page_config(page_title="WorldCupGPT", page_icon="⚽", layout="wide")
st.title("⚽ WorldCupGPT")
st.caption("LangChain agent for World Cup history, stats, and match predictions")

chat_col, trace_col = st.columns([2, 1])

if "agent" not in st.session_state:
    st.session_state.agent = build_agent()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_trace" not in st.session_state:
    st.session_state.last_trace = ""

with chat_col:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about World Cup history or predict a match..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            result = st.session_state.agent.invoke({"input": prompt})
            answer = result["output"]
        finally:
            sys.stdout = old_stdout

        st.session_state.last_trace = buf.getvalue()
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)

with trace_col:
    st.subheader("Agent Reasoning")
    st.caption("Thought / Action / Observation trace from the last query")
    if st.session_state.last_trace:
        st.code(st.session_state.last_trace, language="text")
    else:
        st.info("Ask a question to see the agent reason through tools.")
