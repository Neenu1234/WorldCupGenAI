"""Streamlit chat UI with a live agent reasoning trace. Run: streamlit run src/app.py"""
import io
import random
import sys
from pathlib import Path

# Make `from src...` imports work when Streamlit runs this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src import config
from src.agent import build_agent
from src.preferences import UserPreferences, detect_preferences
from src.vector_store import build_vector_store


def _ensure_vector_store() -> None:
    """Build the Chroma store on first launch (needed for Streamlit Cloud)."""
    if config.CHROMA_DIR.exists() and any(config.CHROMA_DIR.iterdir()):
        return
    with st.spinner("First-time setup: indexing 964 World Cup matches "
                    "(about 2 minutes, only happens once)..."):
        build_vector_store()
from src.visuals import (
    head_to_head_chart,
    top_scorers_chart,
    team_record_chart,
    wc_titles_ranking_chart,
    match_goals_timeline_chart,
    is_ranking_query,
    parse_prediction_query,
    parse_team_query,
    parse_match_goals_query,
)


SAMPLE_QUERIES = {
    "🏆 History": [
        "Who won the 2014 World Cup final?",
        "Who won the 2022 World Cup?",
        "What happened in Brazil vs Germany 2014 semifinal?",
    ],
    "📊 Team stats": [
        "How many World Cup titles does Brazil have?",
        "Who is England all time top scorer?",
        "Tell me about Italy's record",
    ],
    "⚔️ Predictions": [
        "Germany vs France",
        "Brazil vs Argentina",
        "Spain vs Portugal",
    ],
    "⚽ Match goals": [
        "Show goals from Germany vs Brazil 2014",
        "Goals from Argentina vs France 2022",
        "Show goals from England vs Germany 1966",
    ],
}

SURPRISE_QUERIES = [
    "Who has won the most World Cup titles?",
    "Show goals from Germany vs Brazil 2014",
    "Brazil vs Argentina",
    "Who won the 2022 World Cup final?",
    "Tell me about Uruguay's World Cup record",
    "Goals from Argentina vs France 2022",
    "Spain vs Netherlands",
    "What was the score of the 1966 World Cup final?",
    "How many World Cup titles does Germany have?",
    "Show goals from France vs Croatia 2018",
]


st.set_page_config(page_title="WorldCupGPT", page_icon="⚽", layout="wide")
st.title("⚽ WorldCupGPT")
st.caption("LangChain agent for World Cup history, stats, and match predictions")


if "agent" not in st.session_state:
    _ensure_vector_store()
    st.session_state.agent = build_agent()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_trace" not in st.session_state:
    st.session_state.last_trace = ""
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "preferences" not in st.session_state:
    st.session_state.preferences = UserPreferences()


# Sidebar: sample questions + surprise me
with st.sidebar:
    st.header("Try these")
    if st.button("🎲 Surprise me", use_container_width=True):
        st.session_state.pending_query = random.choice(SURPRISE_QUERIES)
        st.rerun()
    st.divider()
    for category, questions in SAMPLE_QUERIES.items():
        st.markdown(f"**{category}**")
        for q in questions:
            if st.button(q, key=f"btn_{q}", use_container_width=True):
                st.session_state.pending_query = q
                st.rerun()
    st.divider()
    st.subheader("Your preferences")
    prefs = st.session_state.preferences
    if prefs.is_empty():
        st.caption("Tell me your favorite team or favorite era and I'll remember "
                   "it across the chat. e.g. \"I'm a Brazil fan\" or "
                   "\"I love the 1990s\".")
    else:
        if prefs.favorite_teams:
            teams_str = ", ".join(f"**{t}**" for t in prefs.favorite_teams)
            label = "Favorite team" if len(prefs.favorite_teams) == 1 else "Favorite teams"
            st.markdown(f"⚽ {label}: {teams_str}")
        if prefs.era_focus:
            st.markdown(f"📅 Era focus: **{prefs.era_focus}**")
        if st.button("Reset preferences", use_container_width=True):
            st.session_state.preferences = UserPreferences()
            st.rerun()
    st.divider()
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_trace = ""
        st.rerun()


chat_col, trace_col = st.columns([2, 1])


SCORER_KEYWORDS = (
    "top scorer", "top scorers", "scorer", "scorers",
    "goal scorer", "leading scorer", "best scorer", "all time top",
    "most goals", "highest scorer",
)

RECORD_KEYWORDS = (
    "record", "win rate", "stats", "statistics", "performance",
    "how have they", "how is", "tell me about",
)

REFUSAL_PATTERNS = (
    "outside the scope",
    "outside my scope",
    "unable to provide",
    "i'm unable",
    "i am unable",
    "i cannot",
    "i can't",
    "i do not have",
    "i don't have",
    "not within my",
    "beyond the scope",
    "not related to",
    "not in this dataset",
    "i cannot help with",
    "i'm sorry",
)


def _is_refusal(answer: str) -> bool:
    """True if the agent refused or said the question is off-topic."""
    if not answer:
        return False
    return any(p in answer.lower() for p in REFUSAL_PATTERNS)


def _is_scorer_query(query: str) -> bool:
    """Check ONLY the user's query (not the AI answer) for scorer keywords.

    Looking at the answer caused false positives — e.g. asking 'Italy's record'
    returned an answer that mentioned top scorers, which then triggered the
    top-scorers chart even though the user did not ask for it.
    """
    return any(k in query.lower() for k in SCORER_KEYWORDS)


def _is_record_query(query: str) -> bool:
    return any(k in query.lower() for k in RECORD_KEYWORDS)


def render_visual_for(query: str, answer: str = "") -> None:
    """If the query or answer maps to a known visual, render it.

    Guard rail: if the agent refused or said the query is off-topic, render
    nothing. This prevents showing a chart for a question the bot did not
    actually answer (e.g. 'what is today's weather?').
    """
    if not query:
        return
    if _is_refusal(answer):
        return
    prefs = st.session_state.preferences

    # 1. Match goals: 'TeamA vs TeamB YYYY' or 'goals from X vs Y YYYY'
    match_info = parse_match_goals_query(query)
    if match_info:
        year, a, b = match_info
        fig = match_goals_timeline_chart(year, a, b)
        if fig is not None:
            st.pyplot(fig)
            return
    # 2. Prediction "X vs Y" (no year)
    teams = parse_prediction_query(query)
    if teams:
        fig = head_to_head_chart(teams[0], teams[1])
        if fig is not None:
            st.pyplot(fig)
            return
    # 3. Ranking / most-winning queries
    if is_ranking_query(query):
        fig = wc_titles_ranking_chart()
        if fig is not None:
            st.pyplot(fig)
            return
    # 4. Scorer-style query → top scorers chart (check QUERY only, not answer)
    if _is_scorer_query(query):
        team = parse_team_query(query) or parse_team_query(answer)
        if team:
            fig = top_scorers_chart(team)
            if fig is not None:
                st.pyplot(fig)
                return
    # 5. Record / stats query about one team → win/draw/loss chart
    if _is_record_query(query):
        team = parse_team_query(query) or parse_team_query(answer)
        if team:
            fig = team_record_chart(team)
            if fig is not None:
                st.pyplot(fig)
                return
    # 6. User has 2+ favorite teams → h2h between favorites.
    # Fire ONLY when the query is genuinely about "them":
    # - no specific year is in the query
    # - no UNRELATED team is mentioned
    # - query uses a pronoun (their / them / they) OR mentions favorites
    #   together with a pronoun-style follow-up
    if len(prefs.favorite_teams) >= 2:
        import re
        has_year = bool(re.search(r"\b(19|20)\d{2}\b", query))
        mentioned_team = parse_team_query(query)
        mentioned_unrelated = (
            mentioned_team is not None
            and mentioned_team not in prefs.favorite_teams
        )
        q_lower = " " + query.lower() + " "
        has_pronoun = any(p in q_lower for p in (" their ", " them ", " they "))
        if not has_year and not mentioned_unrelated and has_pronoun:
            fig = head_to_head_chart(prefs.favorite_teams[0], prefs.favorite_teams[1])
            if fig is not None:
                st.pyplot(fig)


def process_query(prompt: str) -> None:
    """Run a query through the agent and append both messages."""
    # Update preferences from this query
    st.session_state.preferences = detect_preferences(
        prompt, st.session_state.preferences
    )
    pref_string = st.session_state.preferences.to_prompt_string()
    agent_input = f"{pref_string}\n{prompt}" if pref_string else prompt

    st.session_state.messages.append({"role": "user", "content": prompt})

    # Show the user message immediately, then a spinner while the agent works.
    with st.chat_message("user"):
        st.markdown(prompt)

    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        with st.spinner("Thinking… picking the right tool and gathering evidence"):
            result = st.session_state.agent.invoke({"input": agent_input})
        answer = result["output"]
    finally:
        sys.stdout = old_stdout
    st.session_state.last_trace = buf.getvalue()
    st.session_state.messages.append({
        "role": "assistant", "content": answer, "query": prompt,
    })


with chat_col:
    # If a sidebar button was clicked, process its query before re-rendering
    if st.session_state.pending_query:
        pq = st.session_state.pending_query
        st.session_state.pending_query = None
        process_query(pq)

    if not st.session_state.messages:
        st.info("👋 Ask a question below, or click a suggested question on the left. "
                "Try the 🎲 Surprise me button for something random.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("query"):
                render_visual_for(msg["query"], msg.get("content", ""))

    if prompt := st.chat_input("Ask about World Cup history, stats, predictions, or goals..."):
        process_query(prompt)
        st.rerun()

with trace_col:
    st.subheader("Agent Reasoning")
    st.caption("Thought / Action / Observation trace from the last query")
    if st.session_state.last_trace:
        st.code(st.session_state.last_trace, language="text")
    else:
        st.info("Ask a question to see the agent reason through tools.")
