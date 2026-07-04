from __future__ import annotations

import math
import random
import sqlite3
from collections import defaultdict

from . import db
from .models import Match, MatchStatus, Player, TournamentStatus


def next_power_of_two(value: int) -> int:
    if value < 2:
        return 2
    return 2 ** math.ceil(math.log2(value))


def start_tournament(conn: sqlite3.Connection, *, seed: int | None = None) -> None:
    state = db.get_state(conn)
    if state.status != TournamentStatus.REGISTRATION:
        raise ValueError("El torneo ya fue iniciado.")

    players = db.list_players(conn)
    if len(players) < 2:
        raise ValueError("Necesitas al menos 2 participantes.")

    rng = random.Random(seed)
    shuffled = [player.id for player in players]
    rng.shuffle(shuffled)

    bracket_size = next_power_of_two(len(shuffled))
    bye_count = bracket_size - len(shuffled)
    bye_players = shuffled[:bye_count]
    remaining_players = shuffled[bye_count:]

    first_round_match_count = bracket_size // 2
    raw_pairs: list[tuple[int | None, int | None] | None] = [None] * first_round_match_count

    groups = [
        list(range(index, min(index + 2, first_round_match_count)))
        for index in range(0, first_round_match_count, 2)
    ]
    rng.shuffle(groups)
    for group in groups:
        rng.shuffle(group)

    bye_positions: list[int] = []
    for slot_index in range(2):
        for group in groups:
            if len(bye_positions) >= bye_count:
                break
            if slot_index < len(group):
                bye_positions.append(group[slot_index])

    for player_id, position in zip(bye_players, bye_positions):
        raw_pairs[position] = (player_id, None)

    open_positions = [index for index, pair in enumerate(raw_pairs) if pair is None]
    for pair_index, position in enumerate(open_positions):
        player_index = pair_index * 2
        raw_pairs[position] = (remaining_players[player_index], remaining_players[player_index + 1])

    randomized_pairs = []
    for pair in raw_pairs:
        if pair is None:
            continue
        left, right = pair
        if rng.random() < 0.5:
            randomized_pairs.append((left, right))
        else:
            randomized_pairs.append((right, left))

    pairs = []
    for index, (left, right) in enumerate(randomized_pairs):
        pairs.append((1, index + 1, left, right))

    db.create_matches(conn, pairs)
    db.set_state(
        conn,
        status=TournamentStatus.IN_PROGRESS,
        current_round=1,
        bracket_size=bracket_size,
    )
    apply_byes(conn, 1)


def apply_byes(conn: sqlite3.Connection, round_number: int) -> None:
    for match in db.list_matches(conn, round_number):
        if match.status == MatchStatus.COMPLETE:
            continue
        players = [pid for pid in (match.player_a_id, match.player_b_id) if pid is not None]
        if len(players) == 1:
            db.update_match_result(conn, match.id, players[0], None, "Bye automatico", True)


def alive_player_ids(conn: sqlite3.Connection, round_number: int | None = None) -> set[int]:
    state = db.get_state(conn)
    target_round = round_number or state.current_round
    return {match.winner_id for match in db.list_matches(conn, target_round) if match.winner_id is not None}


def current_losers_without_rep(conn: sqlite3.Connection) -> list[Match]:
    state = db.get_state(conn)
    represented = {row["eliminated_player_id"] for row in db.list_representations(conn)}
    pending = []
    for match in db.list_matches(conn, state.current_round):
        if match.status == MatchStatus.COMPLETE and match.loser_id is not None and match.loser_id not in represented:
            pending.append(match)
    return pending


def assign_representative(
    conn: sqlite3.Connection,
    eliminated_player_id: int,
    representative_id: int,
    match_id: int,
) -> None:
    state = db.get_state(conn)
    allowed = alive_player_ids(conn, state.current_round)
    if representative_id not in allowed:
        raise ValueError("El representante tiene que estar clasificado en esta ronda.")
    if representative_id == eliminated_player_id:
        raise ValueError("Un eliminado no puede elegirse a si mismo.")
    db.insert_representation(conn, eliminated_player_id, representative_id, state.current_round, match_id)


def round_can_advance(conn: sqlite3.Connection) -> tuple[bool, str]:
    state = db.get_state(conn)
    matches = db.list_matches(conn, state.current_round)
    open_matches = [match for match in matches if match.status != MatchStatus.COMPLETE]
    if open_matches:
        return False, f"Faltan cerrar {len(open_matches)} partido(s)."
    winners = [match.winner_id for match in matches if match.winner_id is not None]
    if len(winners) == 1:
        return True, "La final esta cerrada. Ya se puede coronar campeon."
    pending_reps = current_losers_without_rep(conn)
    if pending_reps:
        return False, f"Faltan {len(pending_reps)} representante(s)."
    return True, "La ronda esta lista para avanzar."


def advance_round(conn: sqlite3.Connection) -> None:
    can_advance, reason = round_can_advance(conn)
    if not can_advance:
        raise ValueError(reason)

    state = db.get_state(conn)
    winners = [match.winner_id for match in db.list_matches(conn, state.current_round) if match.winner_id is not None]
    if len(winners) == 1:
        db.set_state(
            conn,
            status=TournamentStatus.COMPLETE,
            current_round=state.current_round,
            bracket_size=state.bracket_size,
            champion_id=winners[0],
        )
        return

    next_round = state.current_round + 1
    existing_next_matches = db.list_matches(conn, next_round)
    if existing_next_matches:
        db.set_state(
            conn,
            status=TournamentStatus.IN_PROGRESS,
            current_round=next_round,
            bracket_size=state.bracket_size,
        )
        apply_byes(conn, next_round)
        return

    new_matches = []
    for index in range(0, len(winners), 2):
        player_b = winners[index + 1] if index + 1 < len(winners) else None
        new_matches.append((next_round, index // 2 + 1, winners[index], player_b))

    db.create_matches(conn, new_matches)
    db.set_state(
        conn,
        status=TournamentStatus.IN_PROGRESS,
        current_round=next_round,
        bracket_size=state.bracket_size,
    )
    apply_byes(conn, next_round)


def player_name_map(conn: sqlite3.Connection) -> dict[int, str]:
    return {player.id: player.name for player in db.list_players(conn)}


def name_for(names: dict[int, str], player_id: int | None) -> str:
    if player_id is None:
        return "Bye"
    return names.get(player_id, "Jugador eliminado")


def representative_lookup(conn: sqlite3.Connection) -> dict[int, int]:
    return {row["eliminated_player_id"]: row["representative_id"] for row in db.list_representations(conn)}


def resolve_representative(player_id: int, reps: dict[int, int]) -> int:
    seen = set()
    current = player_id
    while current in reps and current not in seen:
        seen.add(current)
        current = reps[current]
    return current


def teams_by_alive_player(conn: sqlite3.Connection) -> dict[int, list[Player]]:
    players = db.list_players(conn)
    reps = representative_lookup(conn)
    teams: dict[int, list[Player]] = defaultdict(list)
    for player in players:
        teams[resolve_representative(player.id, reps)].append(player)
    return dict(teams)


def round_label(round_number: int, bracket_size: int) -> str:
    remaining = bracket_size // (2 ** (round_number - 1))
    if remaining == 2:
        return "The Final"
    if remaining == 4:
        return "Final Four"
    if remaining == 8:
        return "Elite Eight"
    if remaining == 16:
        return "Sweet Sixteen"
    return f"Round of {remaining}"
