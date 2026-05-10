import { useState } from "react";
import type { EmployerRule, GameMode } from "../types";
import RuleCard from "./RuleCard";
import ModeCard from "./ModeCard";

interface OpeningScreenProps {
  onStart: (alpha: number, mode: GameMode, employerRule: EmployerRule) => Promise<void>;
  error: string;
}

function validateAlpha(raw: string): string | null {
  if (raw.trim() === "") return "Alpha is required.";
  if (!/^\d*\.?\d*$/.test(raw.trim())) return "Alpha must be a number.";
  const n = Number(raw);
  if (isNaN(n)) return "Alpha must be a number.";
  const decimals = raw.includes(".") ? raw.split(".")[1]?.length ?? 0 : 0;
  if (decimals > 2) return "Alpha must have at most 2 decimal places.";
  if (n < 0.01 || n > 0.99) return "Alpha must be between 0.01 and 0.99 (exclusive of 0 and 1).";
  return null;
}

export default function OpeningScreen({ onStart, error }: OpeningScreenProps) {
  const [alphaInput, setAlphaInput] = useState("");
  const [mode, setMode] = useState<GameMode>("blind");
  const [employerRule, setEmployerRule] = useState<EmployerRule>("nash");
  const [alphaError, setAlphaError] = useState("");
  const [starting, setStarting] = useState(false);

  async function handleStart() {
    const err = validateAlpha(alphaInput);
    if (err) {
      setAlphaError(err);
      return;
    }
    setAlphaError("");
    setStarting(true);
    await onStart(Number(alphaInput), mode, employerRule);
    setStarting(false);
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f9fafb",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: "2rem 1rem",
      }}
    >
      <div style={{ width: "100%", maxWidth: 700 }}>
        {/* Header */}
        <div style={{ marginBottom: "1.75rem" }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: "#111827", margin: "0 0 6px" }}>
            Edgeworth Box Bargaining
          </h1>
          <p style={{ fontSize: 14, color: "#6b7280", margin: 0 }}>
            You are a job candidate negotiating salary and benefits with an employer who doesn&apos;t know your preferences.
          </p>
        </div>

        {/* Rule cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: "1.5rem" }}>
          <RuleCard
            icon="🏁"
            title="The employer opens"
            description="The employer makes the first offer based on its beliefs about your preferences."
          />
          <RuleCard
            icon="🔄"
            title="5 rounds of counteroffers"
            description="You have 5 clicks to place counteroffers. The employer responds after each one."
          />
          <RuleCard
            icon="📐"
            title="Cobb-Douglas utilities"
            description="Both parties use Cobb-Douglas utility. The employer doesn't know your alpha."
          />
        </div>

        {/* Utility function panel */}
        <div
          style={{
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: 12,
            padding: "1.25rem 1.5rem",
            marginBottom: "1.25rem",
          }}
        >
          <p style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 600, color: "#111827" }}>
            Your utility function
          </p>
          <p style={{ margin: "0 0 14px", fontSize: 13, color: "#6b7280" }}>
            U(x, y) = x<sup>α</sup> · y<sup>(1−α)</sup>
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <label htmlFor="alpha-input" style={{ fontSize: 13, color: "#374151", whiteSpace: "nowrap" }}>
              Your alpha (α) =
            </label>
            <input
              id="alpha-input"
              type="text"
              maxLength={4}
              placeholder="0.13"
              value={alphaInput}
              onChange={(e) => {
                setAlphaInput(e.target.value);
                if (alphaError) setAlphaError("");
              }}
              style={{
                width: 80,
                padding: "6px 10px",
                border: `1px solid ${alphaError ? "#ef4444" : "#d1d5db"}`,
                borderRadius: 6,
                fontSize: 14,
                outline: "none",
              }}
            />
          </div>
          {alphaError && (
            <p style={{ margin: "6px 0 0", fontSize: 12, color: "#ef4444" }}>{alphaError}</p>
          )}

          {/* Employer rule */}
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 14 }}>
            <span style={{ fontSize: 13, color: "#374151" }}>Employer rule:</span>
            {(["nash", "lens"] as EmployerRule[]).map((r) => (
              <label key={r} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 13, color: "#374151", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="employerRule"
                  value={r}
                  checked={employerRule === r}
                  onChange={() => setEmployerRule(r)}
                />
                {r === "nash" ? "Nash bargaining" : "Lens (endowment-optimal)"}
              </label>
            ))}
          </div>
        </div>

        {/* Mode selection */}
        <div style={{ display: "flex", gap: 12, marginBottom: "1.25rem" }}>
          <ModeCard mode="blind" selected={mode === "blind"} onSelect={() => setMode("blind")} />
          <ModeCard mode="omniscient" selected={mode === "omniscient"} onSelect={() => setMode("omniscient")} />
        </div>

        {/* Footer */}
        <div
          style={{
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: 12,
            padding: "1rem 1.5rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <p style={{ margin: 0, fontSize: 12, color: "#9ca3af", flex: 1, minWidth: 200 }}>
            The employer doesn&apos;t know your alpha and will update its belief about your preferences after each round.
          </p>
          <button
            onClick={() => void handleStart()}
            disabled={starting}
            style={{
              background: "#111827",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "10px 24px",
              fontSize: 14,
              fontWeight: 600,
              cursor: starting ? "not-allowed" : "pointer",
              opacity: starting ? 0.7 : 1,
              whiteSpace: "nowrap",
            }}
          >
            {starting ? "Starting…" : "Start game"}
          </button>
        </div>

        {error && (
          <p style={{ marginTop: 12, color: "#ef4444", fontSize: 13 }}>{error}</p>
        )}
      </div>
    </div>
  );
}
