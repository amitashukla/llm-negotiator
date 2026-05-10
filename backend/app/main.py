from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Repo-root .env (so `uvicorn app.main:app` from /backend still gets Atlas credentials after a correct rename).
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .game_engine import apply_cancel, apply_confirm, apply_propose, start_game
from .models import ActionRequest, SessionResponse, StartGameRequest
from .mongo_games import MongoGameStore
from .store import SQLiteSessionStore

# Bump when debugging deploys; appears in GET / and Docker build verification.
API_BUILD_ID = "negotiator-backend-2026-05-09"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    import logging

    log = logging.getLogger("uvicorn.error")
    paths = sorted({p for r in app.routes if (p := getattr(r, "path", None))})
    log.warning("%s registered routes: %s", API_BUILD_ID, paths)
    yield


app = FastAPI(
    title="Edgeworth Negotiator API",
    version="1.0.0",
    lifespan=_lifespan,
)
mongo_games = MongoGameStore()
store = SQLiteSessionStore(db_path="data/negotiator.db", mongo_games=mongo_games)

# Wildcard: UI may be opened as localhost, 127.0.0.1, or LAN IP (Vite --host 0.0.0.0 in Docker).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    """If this 404s on port 8000, another process is bound there—not this API."""
    return {
        "service": "edgeworth-negotiator-api",
        "build": API_BUILD_ID,
        "health": "/api/health",
        "docs": "/docs",
    }


@app.post("/api/session", response_model=SessionResponse)
def create_session() -> SessionResponse:
    session_id, state = store.create()
    return SessionResponse(session_id=session_id, state=state)


@app.get("/api/session/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(session_id=session_id, state=state)


@app.post("/api/session/{session_id}/start", response_model=SessionResponse)
def start_session(session_id: str, payload: StartGameRequest) -> SessionResponse:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        new_state = start_game(payload.alpha, employer_rule=payload.employer_rule)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store.set(session_id, new_state)
    return SessionResponse(session_id=session_id, state=new_state)


@app.post("/api/session/{session_id}/action", response_model=SessionResponse)
def apply_action(session_id: str, payload: ActionRequest) -> SessionResponse:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.type == "propose":
        if payload.xH is None or payload.yH is None:
            raise HTTPException(status_code=400, detail="xH and yH are required for propose action")
        state = apply_propose(state, payload.xH, payload.yH)
    elif payload.type == "confirm":
        state = apply_confirm(state)
    elif payload.type == "cancel":
        state = apply_cancel(state)
    elif payload.type == "reset":
        state = state.model_copy(
            update={
                "phase": "setup",
                "msg": "",
                "offers": [],
                "history": [],
                "pending": None,
                "alpha": None,
                "endowXH": None,
                "endowYH": None,
                "nashEst": None,
                "trueNash": None,
                "indifferenceCurves": None,
                "endowmentIndifferenceCurves": None,
            }
        )
    else:
        raise HTTPException(status_code=400, detail="Unknown action type")

    store.set(session_id, state)
    store.archive_completed_game(session_id, state)
    return SessionResponse(session_id=session_id, state=state)


@app.get("/api/history")
def get_history() -> list[dict[str, str]]:
    return mongo_games.list_recent()


@app.get("/api/health")
def api_health() -> dict[str, str | list[str]]:
    """Cheap heartbeat; confirms this build includes health routes (404 here means stale/old container)."""
    return {
        "status": "ok",
        "mongodb_endpoints": ["/api/health/mongodb", "/health/mongodb"],
    }


@app.get("/api/health/mongodb")
@app.get("/health/mongodb")
def mongodb_health() -> dict[str, str | bool | int]:
    """Verify Atlas/local connectivity and list count (browse DB name must match MONGODB_DB)."""
    try:
        mongo_games.ping()
        return {
            "ok": True,
            "database": mongo_games.database_name,
            "collection": "games",
            "document_count": mongo_games.games_count(),
        }
    except Exception as exc:  # noqa: BLE001 — surface connection errors to operators
        return {"ok": False, "error": str(exc)}
