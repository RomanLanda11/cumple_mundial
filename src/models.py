from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TournamentStatus(StrEnum):
    REGISTRATION = "registration"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class MatchStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"


@dataclass(frozen=True)
class Player:
    id: int
    name: str
    active: bool


@dataclass(frozen=True)
class Match:
    id: int
    round_number: int
    position: int
    player_a_id: int | None
    player_b_id: int | None
    winner_id: int | None
    loser_id: int | None
    status: MatchStatus
    note: str
    pledge_done: bool


@dataclass(frozen=True)
class TournamentState:
    status: TournamentStatus
    current_round: int
    bracket_size: int
    champion_id: int | None
