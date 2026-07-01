from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .models import Match, MatchStatus, Player, TournamentState, TournamentStatus


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "tournament.db"


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tournament_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            status TEXT NOT NULL,
            current_round INTEGER NOT NULL,
            bracket_size INTEGER NOT NULL,
            champion_id INTEGER REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_number INTEGER NOT NULL,
            position INTEGER NOT NULL,
            player_a_id INTEGER REFERENCES players(id),
            player_b_id INTEGER REFERENCES players(id),
            winner_id INTEGER REFERENCES players(id),
            loser_id INTEGER REFERENCES players(id),
            status TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            pledge_done INTEGER NOT NULL DEFAULT 0,
            UNIQUE(round_number, position)
        );

        CREATE TABLE IF NOT EXISTS representations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eliminated_player_id INTEGER NOT NULL REFERENCES players(id),
            representative_id INTEGER NOT NULL REFERENCES players(id),
            round_number INTEGER NOT NULL,
            match_id INTEGER NOT NULL REFERENCES matches(id),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(eliminated_player_id)
        );
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO tournament_state
            (id, status, current_round, bracket_size, champion_id)
        VALUES (1, ?, 0, 0, NULL)
        """,
        (TournamentStatus.REGISTRATION.value,),
    )
    conn.commit()


def reset_db(conn: sqlite3.Connection) -> None:
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.executescript(
            """
            UPDATE tournament_state
            SET status = 'registration', current_round = 0, bracket_size = 0, champion_id = NULL
            WHERE id = 1;
            DELETE FROM representations;
            DELETE FROM matches;
            DELETE FROM players;
            DELETE FROM sqlite_sequence WHERE name IN ('players', 'matches', 'representations');
            """
        )
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def get_state(conn: sqlite3.Connection) -> TournamentState:
    row = conn.execute("SELECT * FROM tournament_state WHERE id = 1").fetchone()
    return TournamentState(
        status=TournamentStatus(row["status"]),
        current_round=row["current_round"],
        bracket_size=row["bracket_size"],
        champion_id=row["champion_id"],
    )


def set_state(
    conn: sqlite3.Connection,
    *,
    status: TournamentStatus,
    current_round: int,
    bracket_size: int,
    champion_id: int | None = None,
) -> None:
    conn.execute(
        """
        UPDATE tournament_state
        SET status = ?, current_round = ?, bracket_size = ?, champion_id = ?
        WHERE id = 1
        """,
        (status.value, current_round, bracket_size, champion_id),
    )
    conn.commit()


def list_players(conn: sqlite3.Connection) -> list[Player]:
    rows = conn.execute("SELECT * FROM players ORDER BY created_at, id").fetchall()
    return [Player(id=row["id"], name=row["name"], active=bool(row["active"])) for row in rows]


def get_player(conn: sqlite3.Connection, player_id: int | None) -> Player | None:
    if player_id is None:
        return None
    row = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    if not row:
        return None
    return Player(id=row["id"], name=row["name"], active=bool(row["active"]))


def add_player(conn: sqlite3.Connection, name: str) -> None:
    clean_name = " ".join(name.strip().split())
    if not clean_name:
        raise ValueError("El nombre no puede estar vacio.")
    conn.execute("INSERT INTO players (name) VALUES (?)", (clean_name,))
    conn.commit()


def delete_player(conn: sqlite3.Connection, player_id: int) -> None:
    conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
    conn.commit()


def create_matches(conn: sqlite3.Connection, matches: Iterable[tuple[int, int, int | None, int | None]]) -> None:
    conn.executemany(
        """
        INSERT INTO matches (round_number, position, player_a_id, player_b_id, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(round_number, position, a, b, MatchStatus.PENDING.value) for round_number, position, a, b in matches],
    )
    conn.commit()


def update_match_result(
    conn: sqlite3.Connection,
    match_id: int,
    winner_id: int,
    loser_id: int | None,
    note: str,
    pledge_done: bool,
) -> None:
    conn.execute(
        """
        UPDATE matches
        SET winner_id = ?, loser_id = ?, status = ?, note = ?, pledge_done = ?
        WHERE id = ?
        """,
        (winner_id, loser_id, MatchStatus.COMPLETE.value, note.strip(), int(pledge_done), match_id),
    )
    conn.commit()


def clear_match_result(conn: sqlite3.Connection, match_id: int, player_a_id: int | None, player_b_id: int | None) -> None:
    conn.execute(
        """
        UPDATE matches
        SET player_a_id = ?, player_b_id = ?, winner_id = NULL, loser_id = NULL,
            status = ?, note = '', pledge_done = 0
        WHERE id = ?
        """,
        (player_a_id, player_b_id, MatchStatus.PENDING.value, match_id),
    )
    conn.commit()


def set_round_match_players(
    conn: sqlite3.Connection,
    round_number: int,
    position: int,
    player_a_id: int | None,
    player_b_id: int | None,
) -> None:
    row = conn.execute(
        "SELECT * FROM matches WHERE round_number = ? AND position = ?",
        (round_number, position),
    ).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO matches (round_number, position, player_a_id, player_b_id, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (round_number, position, player_a_id, player_b_id, MatchStatus.PENDING.value),
        )
        conn.commit()
        return

    if MatchStatus(row["status"]) == MatchStatus.COMPLETE:
        raise ValueError("No se puede editar un partido ya cerrado en la siguiente ronda.")

    clear_match_result(conn, row["id"], player_a_id, player_b_id)


def list_matches(conn: sqlite3.Connection, round_number: int | None = None) -> list[Match]:
    if round_number is None:
        rows = conn.execute("SELECT * FROM matches ORDER BY round_number, position").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM matches WHERE round_number = ? ORDER BY position",
            (round_number,),
        ).fetchall()
    return [
        Match(
            id=row["id"],
            round_number=row["round_number"],
            position=row["position"],
            player_a_id=row["player_a_id"],
            player_b_id=row["player_b_id"],
            winner_id=row["winner_id"],
            loser_id=row["loser_id"],
            status=MatchStatus(row["status"]),
            note=row["note"],
            pledge_done=bool(row["pledge_done"]),
        )
        for row in rows
    ]


def insert_representation(
    conn: sqlite3.Connection,
    eliminated_player_id: int,
    representative_id: int,
    round_number: int,
    match_id: int,
) -> None:
    conn.execute(
        """
        INSERT INTO representations
            (eliminated_player_id, representative_id, round_number, match_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(eliminated_player_id) DO UPDATE SET
            representative_id = excluded.representative_id,
            round_number = excluded.round_number,
            match_id = excluded.match_id
        """,
        (eliminated_player_id, representative_id, round_number, match_id),
    )
    conn.commit()


def list_representations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM representations ORDER BY created_at, id").fetchall()
