from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .game_engine import apply_cancel, apply_confirm, apply_propose, start_game
from .models import ActionRequest, SessionResponse, StartGameRequest
from .store import SQLiteSessionStore

app = FastAPI(title="Edgeworth Negotiator API", version="1.0.0")
store = SQLiteSessionStore(db_path="data/negotiator.db")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        new_state = start_game(payload.alpha)
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
                "nashEst": None,
                "trueNash": None,
                "indifferenceCurves": None,
            }
        )
    else:
        raise HTTPException(status_code=400, detail="Unknown action type")

    store.set(session_id, state)
    store.archive_completed_game(session_id, state)
    return SessionResponse(session_id=session_id, state=state)


@app.get("/api/history")
def get_history() -> list[dict[str, str]]:
    return store.list_game_history()
