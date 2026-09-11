from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LeadCandidate:
    name: str
    source: str
    url: str
    niche: str
    contact: str
    reason_fit: str
    score: int
