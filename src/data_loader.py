"""Data ingestion, schema validation, and document conversion."""
import pandas as pd
from src import config


REQUIRED_RESULTS_COLS = {
    "date", "home_team", "away_team", "home_score", "away_score",
    "tournament", "city", "country", "neutral",
}


def load_results() -> pd.DataFrame:
    """Load results.csv, validate schema, parse dates."""
    if not config.RESULTS_CSV.exists():
        raise FileNotFoundError(
            f"Missing {config.RESULTS_CSV}. "
            f"Download from {config.DATA_SOURCE_URL} and unzip into data/."
        )
    df = pd.read_csv(config.RESULTS_CSV)
    missing = REQUIRED_RESULTS_COLS - set(df.columns)
    if missing:
        raise ValueError(f"results.csv missing columns: {missing}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "home_team", "away_team"])
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    df = df.dropna(subset=["home_score", "away_score"])
    return df.reset_index(drop=True)


def load_world_cup_matches() -> pd.DataFrame:
    """Just the FIFA World Cup matches (for the RAG history tool)."""
    df = load_results()
    return df[df["tournament"] == "FIFA World Cup"].reset_index(drop=True)


def load_goalscorers() -> pd.DataFrame:
    if not config.GOALSCORERS_CSV.exists():
        raise FileNotFoundError(f"Missing {config.GOALSCORERS_CSV}")
    df = pd.read_csv(config.GOALSCORERS_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna(subset=["date", "scorer"]).reset_index(drop=True)


def match_to_document(row: pd.Series, stage: str = "") -> str:
    """Convert a match row to a natural language string for embedding."""
    venue = "at neutral venue" if row.get("neutral") else f"in {row['city']}, {row['country']}"
    year = row["date"].year
    stage_str = f" ({stage})" if stage else ""
    return (
        f"On {row['date'].date()}, {row['home_team']} played {row['away_team']} "
        f"{venue} during the {year} {row['tournament']}{stage_str}. "
        f"Final score: {row['home_team']} {int(row['home_score'])}, "
        f"{row['away_team']} {int(row['away_score'])}."
    )


def annotate_world_cup_stages(df: pd.DataFrame) -> pd.DataFrame:
    """Mark each World Cup match with its stage (Final, Semi-final, etc.).

    Heuristic: per tournament year, the last 1 match is the Final,
    the previous match (3rd place playoff) is the 3rd Place Playoff,
    and the 2 before that are Semi-finals.
    """
    df = df.copy()
    df["stage"] = ""
    for year, group in df.groupby(df["date"].dt.year):
        sorted_idx = group.sort_values("date").index.tolist()
        if len(sorted_idx) >= 1:
            df.loc[sorted_idx[-1], "stage"] = "Final"
        if len(sorted_idx) >= 2:
            df.loc[sorted_idx[-2], "stage"] = "Third Place Playoff"
        if len(sorted_idx) >= 4:
            df.loc[sorted_idx[-4], "stage"] = "Semi-final"
            df.loc[sorted_idx[-3], "stage"] = "Semi-final"
    return df


if __name__ == "__main__":
    df = load_results()
    print(f"Loaded {len(df):,} international matches")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"World Cup matches: {len(load_world_cup_matches()):,}")
    print(f"Tournaments (top 5): {df['tournament'].value_counts().head().to_dict()}")
