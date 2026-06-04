"""MatchGoals tool: returns the goal-by-goal text for a specific historical match."""
import pandas as pd

from src.data_loader import load_results, load_goalscorers
from src.tools.base import ToolOutput


def _find_match(year: int, team_a: str, team_b: str) -> pd.Series | None:
    df = load_results()
    df["year"] = df["date"].dt.year
    mask = (
        (df["year"] == year)
        & (
            ((df["home_team"] == team_a) & (df["away_team"] == team_b))
            | ((df["home_team"] == team_b) & (df["away_team"] == team_a))
        )
    )
    match = df[mask]
    if match.empty:
        return None
    return match.sort_values("date").iloc[0]


def match_goals(query: str) -> str:
    """Input format: '<TeamA> vs <TeamB> <YYYY>' e.g. 'Germany vs Brazil 2014'."""
    parts = query.strip().split()
    year = None
    for p in parts:
        if p.isdigit() and 1900 < int(p) < 2100:
            year = int(p)
            break
    if not year:
        return ToolOutput(
            answer="Need a year. Use format: 'TeamA vs TeamB YYYY'.",
            limitations="Goal data limited to international matches with recorded scorers.",
        ).to_string()

    q_lower = query.lower()
    if " vs " not in q_lower:
        return ToolOutput(
            answer="Need two teams. Use format: 'TeamA vs TeamB YYYY'.",
        ).to_string()

    idx = q_lower.find(" vs ")
    left = query[:idx].strip()
    right = query[idx + 4:].strip()
    right = right.replace(str(year), "").strip()
    team_a = " ".join(w for w in left.split() if not w.isdigit()).strip()
    team_b = right

    match = _find_match(year, team_a, team_b)
    if match is None:
        return ToolOutput(
            answer=f"No match found for {team_a} vs {team_b} in {year}.",
        ).to_string()

    try:
        gs = load_goalscorers()
    except FileNotFoundError:
        return ToolOutput(
            answer=f"Match found: {match['home_team']} {int(match['home_score'])} to "
                   f"{int(match['away_score'])} {match['away_team']} on {match['date'].date()}. "
                   "Goal scorer data not available.",
        ).to_string()

    goals = gs[gs["date"] == match["date"]].sort_values("minute")
    if goals.empty:
        return ToolOutput(
            answer=f"{match['home_team']} {int(match['home_score'])} to "
                   f"{int(match['away_score'])} {match['away_team']} ({match['date'].date()}). "
                   "No goal scorer details recorded for this match.",
        ).to_string()

    lines = [f"Match: {match['home_team']} {int(match['home_score'])} to "
             f"{int(match['away_score'])} {match['away_team']} on {match['date'].date()}"]
    lines.append(f"({match['tournament']})")
    lines.append("\nGoals:")
    for _, g in goals.iterrows():
        minute = int(g["minute"]) if pd.notna(g["minute"]) else "?"
        own = " (own goal)" if g.get("own_goal") else ""
        pen = " (penalty)" if g.get("penalty") else ""
        lines.append(f"  {minute}'  {g['scorer']} ({g['team']}){own}{pen}")

    return ToolOutput(
        answer="\n".join(lines),
        evidence=[f"From goalscorers.csv: {len(goals)} goals recorded"],
        limitations="Goal data depends on tournament organisers reporting. "
                    "Older or minor matches may have incomplete records.",
    ).to_string()
