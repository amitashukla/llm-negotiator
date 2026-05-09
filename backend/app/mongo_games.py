from __future__ import annotations

import os
import re
from typing import Any, Optional
from urllib.parse import urlparse

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import InvalidURI as MongoInvalidURI


def _normalize_mongodb_uri(raw: str) -> str:
    """Strip Docker/.env junk that breaks pymongo's URI parser (quotes, newlines, duplicate '&')."""
    s = raw.strip().strip('"').strip("'")
    if "\n" in s or "\r" in s:
        raise ValueError(
            "MONGODB_URI must be on a single line in .env — no line breaks inside the connection string."
        )
    # Trailing "&" or "&&" produces "MongoDB URI options are key=value pairs"
    s = re.sub(r"&+$", "", s)
    s = re.sub(r"&{2,}", "&", s)
    return s


class MongoGameStore:
    """Persist completed-game documents for analytics."""

    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None) -> None:
        raw = uri or os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        try:
            self._uri = _normalize_mongodb_uri(raw)
        except ValueError:
            raise
        self._db_name = (db_name or os.environ.get("MONGODB_DB", "negotiator")).strip().strip('"').strip("'")
        self._client: Optional[MongoClient] = None
        self._collection: Optional[Collection[Any]] = None

    @property
    def database_name(self) -> str:
        return self._db_name

    def games_count(self) -> int:
        return int(self._ensure().count_documents({}))

    def _ensure(self) -> Collection[Any]:
        if self._collection is not None:
            return self._collection
        try:
            self._client = MongoClient(self._uri, serverSelectionTimeoutMS=20000)
        except MongoInvalidURI as exc:
            host = urlparse(self._uri).hostname or "?"
            raise MongoInvalidURI(
                f"{exc}. Host={host}. Use one line in .env; query string must be "
                "key=value pairs separated by & (remove stray '&' at end); URL-encode characters in the password."
            ) from exc
        self._collection = self._client[self._db_name]["games"]
        return self._collection

    def insert_completed_game(self, document: dict[str, Any]) -> None:
        # Upsert so a retry after a failed SQLite update does not duplicate documents.
        sid = document["session_id"]
        self._ensure().replace_one({"session_id": sid}, document, upsert=True)

    def ping(self) -> None:
        """Raises if the server cannot be reached (call after _ensure)."""
        self._ensure()
        if self._client is None:
            raise RuntimeError("MongoClient not initialized")
        self._client.admin.command("ping")

    def list_recent(self, limit: int = 100) -> list[dict[str, str]]:
        coll = self._ensure()
        cursor = coll.find({}).sort("created_at", -1).limit(limit)
        out: list[dict[str, str]] = []
        for doc in cursor:
            created = doc.get("created_at")
            created_s = created.isoformat() if hasattr(created, "isoformat") else str(created)
            _id = doc.get("_id")
            out.append(
                {
                    "id": str(_id),
                    "session_id": str(doc.get("session_id", "")),
                    "outcome": str(doc.get("resolution", "")),
                    "created_at": created_s,
                    "candidate_utility_ratio": str(doc.get("candidate_utility_ratio", "")),
                    "product_ratio": str(doc.get("product_ratio", "")),
                }
            )
        return out

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._collection = None
