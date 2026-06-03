"""Common return shape for every custom tool."""
from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class ToolOutput:
    """answer + evidence + limitations, flattened into a single Observation string."""
    answer: str
    evidence: list[Any] = field(default_factory=list)
    limitations: str = ""

    def to_string(self) -> str:
        parts = [self.answer]
        if self.evidence:
            parts.append("\nEvidence:")
            for i, e in enumerate(self.evidence, 1):
                parts.append(f"  {i}. {e}")
        if self.limitations:
            parts.append(f"\nLimitations: {self.limitations}")
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return asdict(self)
