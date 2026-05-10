import { useEffect, useState } from "react";
import { API_BASE, createSession, getSession, sendAction, startGame } from "./api";
import type { AppScreen, EmployerRule, GameMode, GameState } from "./types";
import { validateApiResponse } from "./utils/validate";
import OpeningScreen from "./components/OpeningScreen";
import GameScreen from "./components/GameScreen";
import RevealScreen from "./components/RevealScreen";

const SESSION_KEY = "edgeworth_session_id";

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [screen, setScreen] = useState<AppScreen>("opening");
  const [mode, setMode] = useState<GameMode>("blind");
  const [pendingPoint, setPendingPoint] = useState<{ xH: number; yH: number } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [apiWarnings, setApiWarnings] = useState<string[]>([]);

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        const stored = localStorage.getItem(SESSION_KEY);
        let res;
        if (stored) {
          res = await getSession(stored);
        } else {
          res = await createSession();
          localStorage.setItem(SESSION_KEY, res.session_id);
        }
        setSessionId(res.session_id);
        // Restore to the screen matching the saved phase
        applyState(res.state);
      } catch (e) {
        localStorage.removeItem(SESSION_KEY);
        const net =
          e instanceof TypeError ||
          (e instanceof Error && /network|fetch|failed to fetch|load failed/i.test(e.message));
        setError(
          net
            ? `Cannot reach API at ${API_BASE}. Start the backend and ensure port 8000 is free.`
            : "Could not initialize session. Make sure backend is running."
        );
      } finally {
        setLoading(false);
      }
    };
    void init();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyState(state: GameState, forceScreen?: AppScreen) {
    setGameState(state);
    if (forceScreen) {
      setScreen(forceScreen);
    } else if (state.phase === "setup") {
      setScreen("opening");
    } else if (state.phase === "play") {
      setScreen("game");
    } else if (state.phase === "done") {
      setScreen("reveal");
    }
  }

  async function handleStartGame(alpha: number, selectedMode: GameMode, rule: EmployerRule) {
    if (!sessionId) return;
    try {
      setError("");
      setMode(selectedMode);
      const res = await startGame(sessionId, alpha, rule, selectedMode);
      const warnings = validateApiResponse(res.state, "start");
      if (warnings.length > 0) setApiWarnings(warnings);
      applyState(res.state);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Start failed");
    }
  }

  async function handleChartClick(xH: number, yH: number) {
    if (!sessionId || actionLoading) return;
    setActionLoading(true);
    setPendingPoint({ xH, yH });
    try {
      setError("");
      await sendAction(sessionId, { type: "propose", xH, yH });
      const confirmRes = await sendAction(sessionId, { type: "confirm" });
      const warnings = validateApiResponse(
        confirmRes.state,
        confirmRes.state.phase === "done" ? "done" : "play"
      );
      if (warnings.length > 0) setApiWarnings(warnings);
      applyState(confirmRes.state);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setPendingPoint(null);
      setActionLoading(false);
    }
  }

  async function handlePlayAgain() {
    if (!sessionId) return;
    try {
      setError("");
      setApiWarnings([]);
      const res = await sendAction(sessionId, { type: "reset" });
      applyState(res.state);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 32, color: "#6b7280", fontSize: 14 }}>Loading…</div>
    );
  }

  if (!gameState) {
    return (
      <div style={{ padding: 32, color: "#ef4444", fontSize: 14 }}>
        {error || "Could not load game state."}
      </div>
    );
  }

  if (screen === "game" && gameState.phase === "play") {
    return (
      <GameScreen
        mode={mode}
        gameState={gameState}
        pendingPoint={pendingPoint}
        actionLoading={actionLoading}
        apiWarnings={apiWarnings}
        onDismissWarning={() => setApiWarnings([])}
        onChartClick={(x, y) => void handleChartClick(x, y)}
      />
    );
  }

  if (screen === "reveal" && gameState.phase === "done") {
    return (
      <RevealScreen
        mode={mode}
        gameState={gameState}
        onPlayAgain={() => void handlePlayAgain()}
      />
    );
  }

  // Default: opening screen (setup phase or initial load)
  return (
    <OpeningScreen
      onStart={handleStartGame}
      error={error}
    />
  );
}
