from __future__ import annotations

import logging
import sqlite3
import uuid
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Optional

from .game_engine import make_default_state
from .game_record import build_completed_game_document
from .models import GameState

if TYPE_CHECKING:
    from .mongo_games import MongoGameStore


class SQLiteSessionStore:
    def __init__(self, db_path: str, mongo_games: Optional["MongoGameStore"] = None) -> None:
        self._mongo_games = mongo_games
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
                # Reset archived flag when a game is restarted (phase != "done")
                # so the next completion gets a fresh MongoDB insert attempt.
                if state.phase != "done":
                    self._conn.execute(
                        """
                        UPDATE sessions
                        SET state_json = ?, archived = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE session_id = ?
                        """,
                        (state.model_dump_json(), session_id),
                    )
                else:
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

        # Persist to Atlas/local Mongo first. DB failures must not block gameplay—log and continue.
        if self._mongo_games is not None:
            try:
                doc = build_completed_game_document(session_id, state)
                self._mongo_games.insert_completed_game(doc)
            except ValueError:
                raise
            except Exception:
                logging.exception(
                    "MongoDB archive failed for session %s (check Atlas URI, user password, IP allowlist)",
                    session_id,
                )

        with self._lock:
            row = self._conn.execute(
                "SELECT archived FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None or row["archived"] == 1:
                return
            with self._conn:
                self._conn.execute(
                    "UPDATE sessions SET archived = 1, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (session_id,),
                )
