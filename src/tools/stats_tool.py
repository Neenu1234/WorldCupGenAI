"""TeamStats tool: structured stats (titles, win rate, top scorers) for a team."""
import pandas as pd

from src import config
from src.data_loader import load_results, load_goalscorers
from src.tools.base import ToolOutput


def _load_shootouts() -> pd.DataFrame:
    if not config.SHOOTOUTS_CSV.exists():
        return pd.DataFrame(columns=["date", "home_team", "away_team", "winner"])
    sh = pd.read_csv(config.SHOOTOUTS_CSV)
    sh["date"] = pd.to_datetime(sh["date"], errors="coerce")
    return sh.dropna(subset=["date", "winner"])


def _team_matches(df: pd.DataFrame, team: str) -> pd.DataFrame:
    return df[(df["home_team"] == team) | (df["away_team"] == team)]


def _wc_titles(df: pd.DataFrame, team: str) -> list[int]:
    """Years the team won the World Cup final. Uses shootouts.csv for ties."""
    wc = df[df["tournament"] == "FIFA World Cup"].copy()
    wc["year"] = wc["date"].dt.year
    shootouts = _load_shootouts()
    titles = []
    for year, group in wc.groupby("year"):
        final = group.sort_values("date").tail(1).iloc[0]
        a_score, b_score = final["home_score"], final["away_score"]
        if a_score == b_score:
            # Tied final, look up the shootout winner.
            so = shootouts[shootouts["date"] == final["date"]]
            winner = so.iloc[0]["winner"] if len(so) else None
        else:
            winner = final["home_team"] if a_score > b_score else final["away_team"]
        if winner == team:
            titles.append(int(year))
    return sorted(titles)


def team_stats(team: str) -> str:
    team = team.strip().strip('"').strip("'")
    df = load_results()
    team_df = _team_matches(df, team)

    if team_df.empty:
        return ToolOutput(
            answer=f"No matches found for '{team}'. Check spelling (e.g., 'Germany', 'United States').",
            limitations="Team names must match FIFA records exactly.",
        ).to_string()

    wins = sum(
        (r["home_team"] == team and r["home_score"] > r["away_score"])
        or (r["away_team"] == team and r["away_score"] > r["home_score"])
        for _, r in team_df.iterrows()
    )
    losses = sum(
        (r["home_team"] == team and r["home_score"] < r["away_score"])
        or (r["away_team"] == team and r["away_score"] < r["home_score"])
        for _, r in team_df.iterrows()
    )
    draws = len(team_df) - wins - losses
    win_rate = wins / len(team_df) * 100

    wc_team_df = team_df[team_df["tournament"] == "FIFA World Cup"]
    titles = _wc_titles(df, team)

    # Top scorers (optional, only if goalscorers.csv is available)
    top_scorers = []
    try:
        gs = load_goalscorers()
        team_goals = gs[gs["team"] == team]
        top_scorers = team_goals["scorer"].value_counts().head(5).to_dict()
    except FileNotFoundError:
        pass

    summary = (
        f"{team} stats:\n"
        f"- Total international matches: {len(team_df):,}\n"
        f"- Record: {wins} W, {draws} D, {losses} L (win rate {win_rate:.1f}%)\n"
        f"- World Cup matches: {len(wc_team_df)}\n"
        f"- World Cup titles: {len(titles)}"
        + (f" ({', '.join(map(str, titles))})" if titles else "")
    )
    if top_scorers:
        summary += "\n- All time top scorers: " + ", ".join(
            f"{name} ({goals})" for name, goals in top_scorers.items()
        )

    return ToolOutput(
        answer=summary,
        evidence=[f"Computed from {len(team_df):,} match records"],
        limitations="Stats reflect all international matches in the dataset, not just competitive.",
    ).to_string()
