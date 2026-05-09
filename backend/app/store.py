from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from threading import Lock

from .game_engine import make_default_state
from .models import GameState


class SQLiteSessionStore:
    def __init__(self, db_path: str) -> None:
        self._lock = Lock()
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS game_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    final_state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def create(self) -> tuple[str, GameState]:
        with self._lock:
            session_id = str(uuid.uuid4())
            state = make_default_state()
            with self._conn:
                self._conn.execute(
                    "INSERT INTO sessions (session_id, state_json) VALUES (?, ?)",
                    (session_id, state.model_dump_json()),
                )
            return session_id, state

    def get(self, session_id: str) -> GameState | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT state_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            return GameState.model_validate_json(row["state_json"])

    def set(self, session_id: str, state: GameState) -> None:
        with self._lock:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE sessions
                    SET state_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                    """,
                    (state.model_dump_json(), session_id),
                )

    def archive_completed_game(self, session_id: str, state: GameState) -> None:
        if state.phase != "done":
            return
        with self._lock:
            row = self._conn.execute(
                "SELECT archived FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None or row["archived"] == 1:
                return

            outcome = "agreed" if state.agreed is not None else "no_deal"
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO game_history (session_id, outcome, final_state_json)
                    VALUES (?, ?, ?)
                    """,
                    (session_id, outcome, state.model_dump_json()),
                )
                self._conn.execute(
                    "UPDATE sessions SET archived = 1, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (session_id,),
                )

    def list_game_history(self) -> list[dict[str, str]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, session_id, outcome, created_at
                FROM game_history
                ORDER BY id DESC
                """
            ).fetchall()
            return [
                {
                    "id": str(row["id"]),
                    "session_id": row["session_id"],
                    "outcome": row["outcome"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
