"""Chart helpers for the Streamlit UI. Tools stay text only; UI adds visuals."""
from functools import lru_cache

import matplotlib.pyplot as plt
import pandas as pd

from src.data_loader import load_results, load_goalscorers


def _team_matches(df: pd.DataFrame, team: str) -> pd.DataFrame:
    return df[(df["home_team"] == team) | (df["away_team"] == team)]


def _h2h(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    mask = (
        ((df["home_team"] == a) & (df["away_team"] == b))
        | ((df["home_team"] == b) & (df["away_team"] == a))
    )
    return df[mask].sort_values("date")


def head_to_head_chart(team_a: str, team_b: str):
    """Bar chart of wins/draws/losses between two teams. Returns matplotlib Figure or None."""
    df = load_results()
    h = _h2h(df, team_a, team_b)
    if h.empty:
        return None

    a_wins = sum(
        (r["home_team"] == team_a and r["home_score"] > r["away_score"])
        or (r["away_team"] == team_a and r["away_score"] > r["home_score"])
        for _, r in h.iterrows()
    )
    b_wins = sum(
        (r["home_team"] == team_b and r["home_score"] > r["away_score"])
        or (r["away_team"] == team_b and r["away_score"] > r["home_score"])
        for _, r in h.iterrows()
    )
    draws = len(h) - a_wins - b_wins

    fig, ax = plt.subplots(figsize=(8, 4))
    labels = [f"{team_a} wins", "Draws", f"{team_b} wins"]
    values = [a_wins, draws, b_wins]
    colors = ["#1e88e5", "#9e9e9e", "#e53935"]
    bars = ax.bar(labels, values, color=colors)
    ax.set_title(f"Head to head: {team_a} vs {team_b} ({len(h)} matches total)", fontsize=13)
    ax.set_ylabel("Number of matches")
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            v + 0.1,
            str(v),
            ha="center",
            fontweight="bold",
            fontsize=12,
        )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return fig


def match_goals_timeline_chart(year: int, team_a: str, team_b: str):
    """Horizontal timeline of every goal scored in a specific historical match."""
    df = load_results()
    df = df.copy()
    df["year"] = df["date"].dt.year
    mask = (
        (df["year"] == year)
        & (
            ((df["home_team"] == team_a) & (df["away_team"] == team_b))
            | ((df["home_team"] == team_b) & (df["away_team"] == team_a))
        )
    )
    matches = df[mask]
    if matches.empty:
        return None
    match = matches.sort_values("date").iloc[0]

    try:
        gs = load_goalscorers()
    except FileNotFoundError:
        return None
    goals = gs[gs["date"] == match["date"]].sort_values("minute")
    if goals.empty:
        return None

    home = match["home_team"]
    away = match["away_team"]
    fig, ax = plt.subplots(figsize=(10, max(3, len(goals) * 0.35)))

    for i, (_, g) in enumerate(goals.iterrows()):
        minute = g["minute"] if pd.notna(g["minute"]) else 0
        is_home = g["team"] == home
        color = "#1976d2" if is_home else "#e53935"
        ax.scatter(minute, i, s=200, color=color, zorder=3, edgecolors="white", linewidth=2)
        label = f"{int(minute)}'  {g['scorer']}"
        if g.get("own_goal"):
            label += " (OG)"
        if g.get("penalty"):
            label += " (P)"
        ax.text(minute + 1.5, i, label, va="center", fontsize=10)

    ax.set_xlim(0, max(120, goals["minute"].max() + 20))
    ax.set_ylim(-1, len(goals))
    ax.set_xlabel("Minute")
    ax.set_yticks([])
    ax.axvline(45, color="grey", linestyle="--", alpha=0.4)
    ax.axvline(90, color="grey", linestyle="--", alpha=0.4)
    ax.text(45, len(goals), "HT", ha="center", fontsize=9, color="grey")
    ax.text(90, len(goals), "FT", ha="center", fontsize=9, color="grey")

    title = (f"{home} {int(match['home_score'])} to {int(match['away_score'])} {away}"
             f"  ({year} {match['tournament']})")
    ax.set_title(title, fontsize=13)

    from matplotlib.patches import Patch
    legend = [
        Patch(facecolor="#1976d2", label=home),
        Patch(facecolor="#e53935", label=away),
    ]
    ax.legend(handles=legend, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    plt.tight_layout()
    return fig


def parse_match_goals_query(query: str) -> tuple[int, str, str] | None:
    """Detect 'TeamA vs TeamB YYYY' style queries (prediction query + a year)."""
    import re
    year_match = re.search(r"\b(19|20)\d{2}\b", query)
    if not year_match:
        return None
    year = int(year_match.group())
    cleaned = query.replace(year_match.group(), " ").strip()
    teams = parse_prediction_query(cleaned)
    if not teams:
        return None
    return year, teams[0], teams[1]


def wc_titles_ranking_chart():
    """Horizontal bar chart ranking all World Cup champions by title count."""
    df = load_results()
    wc = df[df["tournament"] == "FIFA World Cup"].copy()
    wc["year"] = wc["date"].dt.year

    # Load shootouts to resolve tied finals
    from src import config
    try:
        sh = pd.read_csv(config.SHOOTOUTS_CSV)
        sh["date"] = pd.to_datetime(sh["date"], errors="coerce")
    except FileNotFoundError:
        sh = pd.DataFrame(columns=["date", "winner"])

    titles = {}
    for year, group in wc.groupby("year"):
        final = group.sort_values("date").tail(1).iloc[0]
        if final["home_score"] == final["away_score"]:
            so = sh[sh["date"] == final["date"]]
            winner = so.iloc[0]["winner"] if len(so) else None
        else:
            winner = final["home_team"] if final["home_score"] > final["away_score"] else final["away_team"]
        if winner:
            titles[winner] = titles.get(winner, 0) + 1

    if not titles:
        return None

    sorted_titles = sorted(titles.items(), key=lambda x: x[1])
    teams = [t for t, _ in sorted_titles]
    counts = [c for _, c in sorted_titles]

    fig, ax = plt.subplots(figsize=(8, max(3, len(teams) * 0.4)))
    colors = ["#ffd700" if c == max(counts) else "#1976d2" for c in counts]
    bars = ax.barh(teams, counts, color=colors)
    ax.set_title("World Cup titles by team (all time)", fontsize=13)
    ax.set_xlabel("Number of titles")
    for bar, v in zip(bars, counts):
        ax.text(v + 0.05, bar.get_y() + bar.get_height() / 2, str(v),
                va="center", fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return fig


def is_ranking_query(query: str) -> bool:
    """Detect queries like 'most winning team', 'best team', 'rank by titles'."""
    q = query.lower()
    triggers = ["most winning", "most successful", "most titles", "best team",
                "top team", "rank", "all winners", "world cup winners",
                "which teams won", "who has the most"]
    return any(t in q for t in triggers)


def top_scorers_chart(team: str, n: int = 10):
    """Horizontal bar chart of top N all-time scorers for a team. Returns Figure or None."""
    try:
        gs = load_goalscorers()
    except FileNotFoundError:
        return None

    team_goals = gs[gs["team"] == team]
    if team_goals.empty:
        return None

    top = team_goals["scorer"].value_counts().head(n)
    if top.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, max(3, len(top) * 0.4)))
    bars = ax.barh(top.index[::-1], top.values[::-1], color="#1976d2")
    ax.set_title(f"{team}: top {len(top)} all time international scorers", fontsize=13)
    ax.set_xlabel("International goals")
    for bar, v in zip(bars, top.values[::-1]):
        ax.text(
            v + 0.5,
            bar.get_y() + bar.get_height() / 2,
            str(v),
            va="center",
            fontweight="bold",
        )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return fig


@lru_cache(maxsize=1)
def _known_teams() -> list[str]:
    """Cached list of all team names in the dataset, longest first."""
    df = load_results()
    teams = pd.concat([df["home_team"], df["away_team"]]).dropna().unique()
    return sorted(teams.tolist(), key=len, reverse=True)


def parse_prediction_query(query: str) -> tuple[str, str] | None:
    """If query is 'X vs Y' style, return (X, Y); otherwise None."""
    q_lower = query.lower()
    for sep in [" vs ", " versus "]:
        if sep in q_lower:
            idx = q_lower.find(sep)
            left = query[:idx].strip()
            right = query[idx + len(sep):].strip().rstrip("?.")
            for prefix in ["predict ", "who will win ", "who would win ",
                           "what is your prediction for ", "match preview for ",
                           "show goals from ", "show me goals from ",
                           "goals from ", "show me the goals from "]:
                if left.lower().startswith(prefix):
                    left = left[len(prefix):].strip()
            if left and right:
                return left, right
    return None


def parse_team_query(query: str) -> str | None:
    """Find the first known team mentioned in the query."""
    q_lower = query.lower()
    for team in _known_teams():
        if team.lower() in q_lower:
            return team
    return None
