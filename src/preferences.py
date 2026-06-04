"""User-preference memory layer.

Tracks two persistent preferences across the session:
- favorite_teams: list of teams the user follows (can be more than one)
- era_focus: the time period they care about (e.g. '1990s', 'modern era')

Preferences are auto-detected from each user query and injected into the
agent's input so answers can be personalized.
"""
import re
from dataclasses import dataclass, asdict, field

from src.visuals import _known_teams


@dataclass
class UserPreferences:
    favorite_teams: list[str] = field(default_factory=list)
    era_focus: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def is_empty(self) -> bool:
        return not (self.favorite_teams or self.era_focus)

    def to_prompt_string(self) -> str:
        if self.is_empty():
            return ""
        parts = []
        if self.favorite_teams:
            joined = ", ".join(self.favorite_teams)
            label = "favourite team" if len(self.favorite_teams) == 1 else "favourite teams"
            parts.append(f"{label} is {joined}")
        if self.era_focus:
            parts.append(f"era of interest is {self.era_focus}")
        return f"[User preferences: {', '.join(parts)}]"


# Triggers where the team name appears AFTER the phrase.
#   e.g. "I'm a Brazil fan", "I support Germany"
AFTER_TRIGGERS = [
    "i'm a ", "im a ", "i am a ", "i support ", "i love ",
    "i follow ", "rooting for ", "i'm rooting for ", "fan of ",
    "my team is ", "my favorite team is ", "my favourite team is ",
    "my teams are ", "my favorite teams are ", "my favourite teams are ",
]

# Triggers where the team name appears BEFORE the phrase.
#   e.g. "Brazil is my favorite team", "Brazil and Argentina are my teams"
BEFORE_TRIGGERS = [
    " is my favorite team", " is my favourite team",
    " are my favorite teams", " are my favourite teams",
    " is my team", " are my teams",
]


def _find_all_teams(text: str) -> list[str]:
    """Return every known team name appearing in `text` (case-insensitive)."""
    t_lower = text.lower()
    found = []
    seen = set()
    for team in _known_teams():
        tl = team.lower()
        if tl in t_lower and team not in seen:
            found.append(team)
            seen.add(team)
    return found


def detect_preferences(query: str, current: UserPreferences) -> UserPreferences:
    """Scan a query for preference signals and return updated preferences."""
    new = UserPreferences(
        favorite_teams=list(current.favorite_teams),
        era_focus=current.era_focus,
    )
    q_lower = query.lower()

    # Detect favorite team(s) using 3 patterns in priority order:
    # 1. AFTER triggers: phrase first, then team name(s).
    # 2. BEFORE triggers: team name(s) first, then phrase.
    # 3. Fallback "<team> fan" pattern.
    new_teams: list[str] = []

    for trigger in AFTER_TRIGGERS:
        if trigger in q_lower:
            idx = q_lower.find(trigger) + len(trigger)
            tail = query[idx: idx + 80]
            for team in _find_all_teams(tail):
                if team not in new_teams and team not in new.favorite_teams:
                    new_teams.append(team)
            if new_teams:
                break

    if not new_teams:
        for trigger in BEFORE_TRIGGERS:
            if trigger in q_lower:
                idx = q_lower.find(trigger)
                head = query[max(0, idx - 80): idx]
                for team in _find_all_teams(head):
                    if team not in new_teams and team not in new.favorite_teams:
                        new_teams.append(team)
                if new_teams:
                    break

    if not new_teams:
        for team in _known_teams():
            if f"{team.lower()} fan" in q_lower and team not in new.favorite_teams:
                new_teams.append(team)

    new.favorite_teams.extend(new_teams)

    # Era: prefer a decade, then common era phrases.
    decade = re.search(r"\b((?:19|20)\d0)s\b", q_lower)
    if decade:
        new.era_focus = f"{decade.group(1)}s"
    elif "modern era" in q_lower or "modern football" in q_lower:
        new.era_focus = "modern era"
    elif "classic era" in q_lower or "old school" in q_lower or "golden age" in q_lower:
        new.era_focus = "classic era"

    return new
