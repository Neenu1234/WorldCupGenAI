"""MatchPredictor tool: head to head + recent form features fed to an LLM."""
import pandas as pd
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src import config
from src.data_loader import load_results
from src.tools.base import ToolOutput


PREDICT_PROMPT = PromptTemplate.from_template(
    """You are a football analyst writing a short match preview.

Teams: {team_a} vs {team_b}

Head to head (last {h2h_n} meetings):
{h2h_table}

Recent form ({recent_n} most recent matches each):
{team_a}: {form_a}
{team_b}: {form_b}

Write a 4 to 6 sentence preview ending with a predicted outcome
(e.g., "Prediction: {team_a} to win 2 to 1"). Be specific about which
historical results back your prediction. Do not invent stats."""
)


def _team_matches(df: pd.DataFrame, team: str) -> pd.DataFrame:
    return df[(df["home_team"] == team) | (df["away_team"] == team)].sort_values("date")


def _recent_form(df: pd.DataFrame, team: str, n: int) -> list[str]:
    recent = _team_matches(df, team).tail(n)
    out = []
    for _, r in recent.iterrows():
        opp = r["away_team"] if r["home_team"] == team else r["home_team"]
        own = r["home_score"] if r["home_team"] == team else r["away_score"]
        their = r["away_score"] if r["home_team"] == team else r["home_score"]
        result = "W" if own > their else ("L" if own < their else "D")
        out.append(f"{result} vs {opp} ({int(own)} to {int(their)}, {r['date'].date()})")
    return out


def _h2h(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    mask = (
        ((df["home_team"] == a) & (df["away_team"] == b))
        | ((df["home_team"] == b) & (df["away_team"] == a))
    )
    return df[mask].sort_values("date")


def predict_match(query: str) -> str:
    if " vs " not in query.lower():
        return ToolOutput(
            answer="Could not parse teams. Use format: TeamA vs TeamB.",
            limitations="Tool requires exact team names as in FIFA records.",
        ).to_string()

    parts = [p.strip() for p in query.split(" vs ", 1)]
    if len(parts) != 2:
        parts = [p.strip() for p in query.split(" VS ", 1)]
    team_a, team_b = parts[0], parts[1]

    df = load_results()
    h2h = _h2h(df, team_a, team_b)
    form_a = _recent_form(df, team_a, config.RECENT_FORM_WINDOW)
    form_b = _recent_form(df, team_b, config.RECENT_FORM_WINDOW)

    if len(h2h) < config.H2H_MIN_MATCHES:
        h2h_table = f"No recorded head to head matches between {team_a} and {team_b}."
    else:
        rows = [
            f"{r['date'].date()}: {r['home_team']} {int(r['home_score'])} to "
            f"{int(r['away_score'])} {r['away_team']} ({r['tournament']})"
            for _, r in h2h.tail(10).iterrows()
        ]
        h2h_table = "\n".join(rows)

    llm = ChatOpenAI(model=config.LLM_MODEL_HEAVY, temperature=config.TEMPERATURE)
    prompt = PREDICT_PROMPT.format(
        team_a=team_a,
        team_b=team_b,
        h2h_n=min(10, len(h2h)),
        h2h_table=h2h_table,
        recent_n=config.RECENT_FORM_WINDOW,
        form_a="; ".join(form_a) if form_a else "no recent matches found",
        form_b="; ".join(form_b) if form_b else "no recent matches found",
    )
    answer = llm.invoke(prompt).content

    return ToolOutput(
        answer=answer,
        evidence=h2h_table.split("\n") if "No recorded" not in h2h_table else [],
        limitations=(
            "Prediction is based only on historical results and recent form "
            "from the martj42 dataset. Does not account for injuries, lineups, "
            "weather, or current squad composition."
        ),
    ).to_string()
