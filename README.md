# Edgeworth Negotiator (React + FastAPI)

This project is split into:

- `frontend`: React + Vite + TypeScript UI
- `backend`: FastAPI game engine + API

The frontend sends actions to the backend and renders returned game state.

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs on `http://127.0.0.1:8000`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://127.0.0.1:5173`.

## Run with Docker Compose

From project root:

```bash
docker compose up --build
```

This starts:

- FastAPI backend on `http://127.0.0.1:8000`
- React frontend on `http://127.0.0.1:5173`

To stop:

```bash
docker compose down
```

## Persistence behavior

- Session state is stored server-side in SQLite at `backend/data/negotiator.db` (per session ID).
- Frontend stores session ID in `localStorage`, so state survives browser refresh.
- State survives backend restarts as long as the SQLite file is preserved.
- Completed games are archived in `game_history` for future analytics/database work.

## Running the test with LLMs

`cd backend && pip install -r requirements.txt`
`python run_llm_negotiation.py --model llama-3.3-70b-versatile`

Optional additional parameters: `--fixed-endowment, --seed N, --temperature 0.7, --no-mongo.`