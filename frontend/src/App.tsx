import { useEffect, useMemo, useRef, useState } from "react";
import { createSession, getSession, sendAction, startGame } from "./api";
import type { GameState, Offer } from "./types";

const W = 10;
const H = 10;
const ROUNDS = 5;
const CANVAS = 420;
const PAD = 48;
const INNER = CANVAS - 2 * PAD;
const SESSION_KEY = "edgeworth_session_id";

const COLORS = {
  human: "#185FA5",
  ai: "#993C1D",
  endow: "#5F5E5A",
  offer: "#BA7517",
  agree: "#1D9E75"
};

function toCanvas(xH: number, yH: number) {
  return { cx: PAD + (xH / W) * INNER, cy: PAD + ((H - yH) / H) * INNER };
}

function fromCanvas(cx: number, cy: number) {
  return { xH: ((cx - PAD) / INNER) * W, yH: H - ((cy - PAD) / INNER) * H };
}

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [alphaInput, setAlphaInput] = useState("0.5");
  const [hover, setHover] = useState<{ xH: number; yH: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        const storedSessionId = localStorage.getItem(SESSION_KEY);
        if (storedSessionId) {
          const existing = await getSession(storedSessionId);
          setSessionId(existing.session_id);
          setState(existing.state);
          return;
        }
        const created = await createSession();
        localStorage.setItem(SESSION_KEY, created.session_id);
        setSessionId(created.session_id);
        setState(created.state);
      } catch {
        localStorage.removeItem(SESSION_KEY);
        setError("Could not initialize session. Make sure backend is running.");
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, []);

  const lastHumanOffer = useMemo(
    () => state?.offers.filter((o) => o.type === "human").slice(-1)[0],
    [state?.offers]
  );
  const lastAIOffer = useMemo(
    () => state?.offers.filter((o) => o.type === "ai").slice(-1)[0],
    [state?.offers]
  );

  const endowC = toCanvas(5, 5);
  const pendingC = state?.pending ? toCanvas(state.pending.xH, state.pending.yH) : null;
  const hoverC = hover ? toCanvas(hover.xH, hover.yH) : null;

  async function syncAction(
    payload: { type: "propose"; xH: number; yH: number } | { type: "confirm" | "cancel" | "reset" }
  ) {
    if (!sessionId) return;
    try {
      setError("");
      const res = await sendAction(sessionId, payload);
      setState(res.state);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    }
  }

  async function handleStart() {
    if (!sessionId) return;
    try {
      setError("");
      const parsed = Number(alphaInput);
      const res = await startGame(sessionId, parsed);
      setState(res.state);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Start failed");
    }
  }

  function handleSVGClick(e: React.MouseEvent<SVGSVGElement>) {
    if (!state || state.phase !== "play") return;
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const sx = CANVAS / rect.width;
    const sy = CANVAS / rect.height;
    const { xH, yH } = fromCanvas((e.clientX - rect.left) * sx, (e.clientY - rect.top) * sy);
    if (xH < 0 || xH > W || yH < 0 || yH > H) return;
    void syncAction({ type: "propose", xH, yH });
  }

  function handleSVGMove(e: React.MouseEvent<SVGSVGElement>) {
    if (!state || state.phase !== "play") return;
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const sx = CANVAS / rect.width;
    const sy = CANVAS / rect.height;
    const { xH, yH } = fromCanvas((e.clientX - rect.left) * sx, (e.clientY - rect.top) * sy);
    setHover(xH >= 0 && xH <= W && yH >= 0 && yH <= H ? { xH, yH } : null);
  }

  if (loading) {
    return <div style={{ padding: 24 }}>Loading...</div>;
  }

  if (!state) {
    return <div style={{ padding: 24 }}>{error || "Could not load state."}</div>;
  }

  return (
    <div style={{ padding: "1.5rem 1rem", color: "#1f2937" }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 0.25rem" }}>Edgeworth box bargaining</h2>
      <p style={{ fontSize: 13, color: "#6b7280", margin: "0 0 1.25rem" }}>
        5-round alternating offers with FastAPI game engine and React UI
      </p>

      {state.phase === "setup" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 420 }}>
          <div style={{ background: "#ffffff", borderRadius: 10, border: "1px solid #e5e7eb", padding: "1rem 1.25rem" }}>
            <p style={{ margin: "0 0 8px", fontSize: 14, fontWeight: 600 }}>Your utility function</p>
            <p style={{ margin: "0 0 12px", fontSize: 13, color: "#6b7280" }}>
              U_H = x^alpha * y^(1-alpha) and AI does not know your alpha
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <label style={{ fontSize: 13, color: "#6b7280" }}>Your alpha =</label>
              <input
                type="number"
                min="0.01"
                max="0.99"
                step="0.01"
                value={alphaInput}
                onChange={(e) => setAlphaInput(e.target.value)}
                style={{ width: 80 }}
              />
            </div>
          </div>
          <button onClick={handleStart} style={{ alignSelf: "flex-start" }}>
            Start game
          </button>
        </div>
      )}

      {(state.phase === "play" || state.phase === "done") && (
        <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
          <div style={{ flexShrink: 0 }}>
            <svg
              ref={svgRef}
              width={CANVAS}
              height={CANVAS}
              viewBox={`0 0 ${CANVAS} ${CANVAS}`}
              style={{ cursor: state.phase === "play" ? "crosshair" : "default", display: "block", maxWidth: "100%" }}
              onClick={handleSVGClick}
              onMouseMove={handleSVGMove}
              onMouseLeave={() => setHover(null)}
            >
              <rect x={PAD} y={PAD} width={INNER} height={INNER} fill="#fff" stroke="#d1d5db" strokeWidth={1} />

              {[0, 2, 4, 6, 8, 10].map((v) => {
                const cx = PAD + (v / W) * INNER;
                const cy = PAD + ((H - v) / H) * INNER;
                return (
                  <g key={v}>
                    <line x1={cx} y1={PAD + INNER} x2={cx} y2={PAD + INNER + 4} stroke="#9ca3af" strokeWidth={1} />
                    <text x={cx} y={PAD + INNER + 14} textAnchor="middle" fontSize={10} fill="#6b7280">
                      {v}
                    </text>
                    <line x1={PAD - 4} y1={cy} x2={PAD} y2={cy} stroke="#9ca3af" strokeWidth={1} />
                    <text x={PAD - 8} y={cy + 4} textAnchor="end" fontSize={10} fill="#6b7280">
                      {v}
                    </text>
                  </g>
                );
              })}

              <circle cx={endowC.cx} cy={endowC.cy} r={5} fill={COLORS.endow} opacity={0.8} />

              {state.offers.map((o: Offer, i: number) => {
                const c = toCanvas(o.xH, o.yH);
                const col = o.type === "human" ? COLORS.human : COLORS.ai;
                return (
                  <g key={`${o.type}-${o.round}-${i}`}>
                    {i > 0 && (() => {
                      const p = toCanvas(state.offers[i - 1].xH, state.offers[i - 1].yH);
                      return <line x1={p.cx} y1={p.cy} x2={c.cx} y2={c.cy} stroke="#9ca3af" strokeWidth={1} strokeDasharray="2,2" />;
                    })()}
                    <circle cx={c.cx} cy={c.cy} r={6} fill={col} opacity={0.85} />
                    <text x={c.cx + 8} y={c.cy + 4} fontSize={10} fill={col}>
                      {o.type === "human" ? "H" : "A"}
                      {o.round}
                    </text>
                  </g>
                );
              })}

              {state.agreed && (() => {
                const c = toCanvas(state.agreed.xH, state.agreed.yH);
                return (
                  <>
                    <circle cx={c.cx} cy={c.cy} r={10} fill="none" stroke={COLORS.agree} strokeWidth={2} />
                    <circle cx={c.cx} cy={c.cy} r={4} fill={COLORS.agree} />
                  </>
                );
              })()}

              {pendingC && (
                <>
                  <line x1={endowC.cx} y1={endowC.cy} x2={pendingC.cx} y2={pendingC.cy} stroke={COLORS.offer} strokeWidth={1} strokeDasharray="3,2" />
                  <circle cx={pendingC.cx} cy={pendingC.cy} r={7} fill="none" stroke={COLORS.offer} strokeWidth={2} />
                  <circle cx={pendingC.cx} cy={pendingC.cy} r={3} fill={COLORS.offer} />
                </>
              )}

              {hoverC && !state.pending && (
                <>
                  <line x1={hoverC.cx} y1={PAD} x2={hoverC.cx} y2={PAD + INNER} stroke="#9ca3af" strokeWidth={1} strokeDasharray="2,2" />
                  <line x1={PAD} y1={hoverC.cy} x2={PAD + INNER} y2={hoverC.cy} stroke="#9ca3af" strokeWidth={1} strokeDasharray="2,2" />
                  <circle cx={hoverC.cx} cy={hoverC.cy} r={4} fill="none" stroke="#6b7280" strokeWidth={1.5} />
                </>
              )}
            </svg>
          </div>

          <div style={{ flex: 1, minWidth: 220, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", gap: 6 }}>
              {Array.from({ length: ROUNDS }, (_, i) => (
                <div
                  key={i}
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 6,
                    background: i + 1 < state.round ? "#dcfce7" : i + 1 === state.round && state.phase === "play" ? "#dbeafe" : "#f3f4f6",
                    border: "1px solid #d1d5db",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 13,
                    fontWeight: 600
                  }}
                >
                  {i + 1}
                </div>
              ))}
            </div>

            <div style={{ background: "#fff", borderRadius: 8, border: "1px solid #e5e7eb", padding: "0.75rem 1rem", fontSize: 13, color: "#4b5563" }}>
              {state.msg}
            </div>

            {state.pending && state.phase === "play" && (
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => void syncAction({ type: "confirm" })}>Confirm offer</button>
                <button onClick={() => void syncAction({ type: "cancel" })}>Cancel</button>
              </div>
            )}

            <div style={{ background: "#fff", borderRadius: 10, border: "1px solid #e5e7eb", padding: "1rem 1.25rem" }}>
              <p style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600 }}>AI belief about your alpha</p>
              <p style={{ margin: "0 0 4px", fontSize: 12, color: "#6b7280" }}>
                Posterior: Beta({state.posterior.a.toFixed(1)}, {state.posterior.b.toFixed(1)})
              </p>
              <p style={{ margin: "0 0 4px", fontSize: 12, color: "#6b7280" }}>
                Posterior mean alpha_hat = <strong>{state.alphaHat.toFixed(3)}</strong> and true alpha ={" "}
                <strong>{state.alpha ?? "-"}</strong>
              </p>
              {state.nashEst && (
                <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>
                  Nash estimate: you ({state.nashEst.xH.toFixed(2)}, {state.nashEst.yH.toFixed(2)})
                </p>
              )}
            </div>

            {state.history.length > 0 && (
              <div style={{ background: "#fff", borderRadius: 10, border: "1px solid #e5e7eb", padding: "1rem 1.25rem" }}>
                <p style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600 }}>Round history</p>
                {state.history.map((h) => (
                  <div key={h.round} style={{ fontSize: 12, color: "#6b7280", marginBottom: 6 }}>
                    <strong>R{h.round}</strong> You: ({h.human.xH.toFixed(2)}, {h.human.yH.toFixed(2)}) AI: ({h.ai.xH.toFixed(2)}, {h.ai.yH.toFixed(2)}) alpha_hat{" "}
                    {h.alphaHat.toFixed(2)}
                  </div>
                ))}
              </div>
            )}

            {state.phase === "done" && (
              <button onClick={() => void syncAction({ type: "reset" })}>Play again</button>
            )}

            {lastHumanOffer && lastAIOffer && (
              <div style={{ fontSize: 12, color: "#6b7280" }}>
                Last human offer: ({lastHumanOffer.xH.toFixed(2)}, {lastHumanOffer.yH.toFixed(2)}) | Last AI offer: (
                {lastAIOffer.xH.toFixed(2)}, {lastAIOffer.yH.toFixed(2)})
              </div>
            )}
          </div>
        </div>
      )}

      {error && (
        <p style={{ marginTop: 12, color: "#b91c1c", fontSize: 13 }}>
          {error}
        </p>
      )}
    </div>
  );
}
