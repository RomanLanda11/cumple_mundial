from __future__ import annotations

import sqlite3

import pytest

from src import db
from src.models import MatchStatus, TournamentStatus
from src.tournament import (
    advance_round,
    assign_representative,
    current_losers_without_rep,
    next_power_of_two,
    round_label,
    round_can_advance,
    start_tournament,
    teams_by_alive_player,
)


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    db.init_db(connection)
    return connection


def add_players(conn: sqlite3.Connection, amount: int) -> None:
    for index in range(amount):
        db.add_player(conn, f"Jugador {index + 1}")


@pytest.mark.parametrize("amount", [35, 36, 47, 60])
def test_start_tournament_uses_next_power_of_two_with_byes(conn: sqlite3.Connection, amount: int) -> None:
    add_players(conn, amount)

    start_tournament(conn, seed=10)

    state = db.get_state(conn)
    matches = db.list_matches(conn, 1)
    complete_byes = [match for match in matches if match.status == MatchStatus.COMPLETE and match.loser_id is None]

    assert state.status == TournamentStatus.IN_PROGRESS
    assert state.bracket_size == next_power_of_two(amount)
    assert len(matches) == state.bracket_size // 2
    assert len(complete_byes) == state.bracket_size - amount


def test_cannot_advance_with_open_matches(conn: sqlite3.Connection) -> None:
    add_players(conn, 4)
    start_tournament(conn, seed=1)

    can_advance, reason = round_can_advance(conn)

    assert can_advance is False
    assert "Faltan cerrar" in reason
    with pytest.raises(ValueError, match="Faltan cerrar"):
        advance_round(conn)


def test_cannot_advance_until_losers_have_representatives(conn: sqlite3.Connection) -> None:
    add_players(conn, 4)
    start_tournament(conn, seed=1)
    match_1, match_2 = db.list_matches(conn, 1)
    db.update_match_result(conn, match_1.id, match_1.player_a_id, match_1.player_b_id, "", False)
    db.update_match_result(conn, match_2.id, match_2.player_a_id, match_2.player_b_id, "", False)

    can_advance, reason = round_can_advance(conn)

    assert can_advance is False
    assert "representante" in reason
    assert len(current_losers_without_rep(conn)) == 2


def test_assign_representatives_and_advance_round(conn: sqlite3.Connection) -> None:
    add_players(conn, 4)
    start_tournament(conn, seed=1)
    match_1, match_2 = db.list_matches(conn, 1)
    db.update_match_result(conn, match_1.id, match_1.player_a_id, match_1.player_b_id, "", True)
    db.update_match_result(conn, match_2.id, match_2.player_a_id, match_2.player_b_id, "", True)
    assign_representative(conn, match_1.player_b_id, match_1.player_a_id, match_1.id)
    assign_representative(conn, match_2.player_b_id, match_2.player_a_id, match_2.id)

    advance_round(conn)

    state = db.get_state(conn)
    next_matches = db.list_matches(conn, 2)
    assert state.current_round == 2
    assert len(next_matches) == 1
    assert next_matches[0].player_a_id == match_1.player_a_id
    assert next_matches[0].player_b_id == match_2.player_a_id


def test_representation_chain_moves_people_to_final_leader(conn: sqlite3.Connection) -> None:
    add_players(conn, 4)
    start_tournament(conn, seed=1)
    match_1, match_2 = db.list_matches(conn, 1)
    db.update_match_result(conn, match_1.id, match_1.player_a_id, match_1.player_b_id, "", True)
    db.update_match_result(conn, match_2.id, match_2.player_a_id, match_2.player_b_id, "", True)
    assign_representative(conn, match_1.player_b_id, match_1.player_a_id, match_1.id)
    assign_representative(conn, match_2.player_b_id, match_2.player_a_id, match_2.id)
    advance_round(conn)

    final = db.list_matches(conn, 2)[0]
    db.update_match_result(conn, final.id, final.player_b_id, final.player_a_id, "", True)
    assign_representative(conn, final.player_a_id, final.player_b_id, final.id)
    advance_round(conn)

    teams = teams_by_alive_player(conn)
    champion_team = {player.id for player in teams[final.player_b_id]}

    assert final.player_a_id in champion_team
    assert match_1.player_b_id in champion_team


def test_final_can_close_without_assigning_runner_up_representative(conn: sqlite3.Connection) -> None:
    add_players(conn, 4)
    start_tournament(conn, seed=1)
    match_1, match_2 = db.list_matches(conn, 1)
    db.update_match_result(conn, match_1.id, match_1.player_a_id, match_1.player_b_id, "", True)
    db.update_match_result(conn, match_2.id, match_2.player_a_id, match_2.player_b_id, "", True)
    assign_representative(conn, match_1.player_b_id, match_1.player_a_id, match_1.id)
    assign_representative(conn, match_2.player_b_id, match_2.player_a_id, match_2.id)
    advance_round(conn)

    final = db.list_matches(conn, 2)[0]
    db.update_match_result(conn, final.id, final.player_a_id, final.player_b_id, "", True)
    can_advance, reason = round_can_advance(conn)
    advance_round(conn)

    state = db.get_state(conn)
    assert can_advance is True
    assert "campeon" in reason
    assert state.status == TournamentStatus.COMPLETE
    assert state.champion_id == final.player_a_id


def test_reset_db_after_completed_tournament_clears_foreign_keys(conn: sqlite3.Connection) -> None:
    add_players(conn, 4)
    start_tournament(conn, seed=1)
    match_1, match_2 = db.list_matches(conn, 1)
    db.update_match_result(conn, match_1.id, match_1.player_a_id, match_1.player_b_id, "", True)
    db.update_match_result(conn, match_2.id, match_2.player_a_id, match_2.player_b_id, "", True)
    assign_representative(conn, match_1.player_b_id, match_1.player_a_id, match_1.id)
    assign_representative(conn, match_2.player_b_id, match_2.player_a_id, match_2.id)
    advance_round(conn)
    final = db.list_matches(conn, 2)[0]
    db.update_match_result(conn, final.id, final.player_a_id, final.player_b_id, "", True)
    advance_round(conn)

    db.reset_db(conn)

    state = db.get_state(conn)
    assert state.status == TournamentStatus.REGISTRATION
    assert state.champion_id is None
    assert db.list_players(conn) == []
    assert db.list_matches(conn) == []


def test_round_labels_use_march_madness_names() -> None:
    assert round_label(1, 64) == "Round of 64"
    assert round_label(2, 64) == "Round of 32"
    assert round_label(3, 64) == "Sweet Sixteen"
    assert round_label(4, 64) == "Elite Eight"
    assert round_label(5, 64) == "Final Four"
    assert round_label(6, 64) == "The Final"


def test_advance_round_uses_precreated_drag_slots(conn: sqlite3.Connection) -> None:
    add_players(conn, 4)
    start_tournament(conn, seed=1)
    match_1, match_2 = db.list_matches(conn, 1)
    db.update_match_result(conn, match_1.id, match_1.player_a_id, match_1.player_b_id, "", True)
    db.update_match_result(conn, match_2.id, match_2.player_a_id, match_2.player_b_id, "", True)
    assign_representative(conn, match_1.player_b_id, match_1.player_a_id, match_1.id)
    assign_representative(conn, match_2.player_b_id, match_2.player_a_id, match_2.id)
    db.set_round_match_players(conn, 2, 1, match_2.player_a_id, match_1.player_a_id)

    advance_round(conn)

    state = db.get_state(conn)
    next_matches = db.list_matches(conn, 2)
    assert state.current_round == 2
    assert len(next_matches) == 1
    assert next_matches[0].player_a_id == match_2.player_a_id
    assert next_matches[0].player_b_id == match_1.player_a_id
