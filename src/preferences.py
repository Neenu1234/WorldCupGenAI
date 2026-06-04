"""User-preference memory layer.

Tracks two persistent preferences across the session:
- favorite_team: the team the user follows
- era_focus: the time period they care about (e.g. '1990s', 'modern era')

Preferences are auto-detected from each user query and injected into the
agent's input so answers can be personalized.
"""
import re
from dataclasses import dataclass, asdict

from src.visuals import _known_teams


@dataclass
class UserPreferences:
    favorite_team: str | None = None
    era_focus: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def is_empty(self) -> bool:
        return not (self.favorite_team or self.era_focus)

    def to_prompt_string(self) -> str:
        if self.is_empty():
            return ""
        parts = []
        if self.favorite_team:
            parts.append(f"favourite team is {self.favorite_team}")
        if self.era_focus:
            parts.append(f"era of interest is {self.era_focus}")
        return f"[User preferences: {', '.join(parts)}]"


FAVORITE_TRIGGERS = [
    "i'm a ", "im a ", "i am a ", "i support ", "i love ",
    "my team is ", "my favorite team is ", "my favourite team is ",
    "i follow ", "fan of ", "rooting for ", "i'm rooting for ",
]


def detect_preferences(query: str, current: UserPreferences) -> UserPreferences:
    """Scan a query for preference signals and return updated preferences."""
    new = UserPreferences(
        favorite_team=current.favorite_team,
        era_focus=current.era_focus,
    )
    q_lower = query.lower()

    # Detect favorite team in priority order:
    # 1. Explicit trigger phrase ("i'm a", "i support", etc.) then team name nearby.
    # 2. Pattern "<team> fan" anywhere (e.g. "brazil fan", "argentina fan").
    for trigger in FAVORITE_TRIGGERS:
        if trigger in q_lower:
            idx = q_lower.find(trigger) + len(trigger)
            tail = query[idx: idx + 60]
            for team in _known_teams():
                if team.lower() in tail.lower()[: len(team) + 5]:
                    new.favorite_team = team
                    break
            if new.favorite_team != current.favorite_team:
                break

    if new.favorite_team == current.favorite_team:
        # Fallback: "<team> fan" anywhere in the query.
        for team in _known_teams():
            if f"{team.lower()} fan" in q_lower:
                new.favorite_team = team
                break

    # Era: prefer a decade (e.g. "1990s"), else recognise common era phrases.
    decade = re.search(r"\b((?:19|20)\d0)s\b", q_lower)
    if decade:
        new.era_focus = f"{decade.group(1)}s"
    elif "modern era" in q_lower or "modern football" in q_lower:
        new.era_focus = "modern era"
    elif "classic era" in q_lower or "old school" in q_lower or "golden age" in q_lower:
        new.era_focus = "classic era"

    return new
