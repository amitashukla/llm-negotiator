import type { GameMode } from "../types";

interface ModeCardProps {
  mode: GameMode;
  selected: boolean;
  onSelect: () => void;
}

function EyeIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

const BLIND_COLOR = "#1D9E75";
const OMNISCIENT_COLOR = "#7F77DD";

export default function ModeCard({ mode, selected, onSelect }: ModeCardProps) {
  const isBlind = mode === "blind";
  const accentColor = isBlind ? BLIND_COLOR : OMNISCIENT_COLOR;

  return (
    <button
      onClick={onSelect}
      style={{
        flex: 1,
        background: "#fff",
        border: selected ? `2px solid ${accentColor}` : "0.5px solid #d1d5db",
        borderRadius: 12,
        padding: "1.25rem 1rem",
        cursor: "pointer",
        textAlign: "left",
        position: "relative",
        transition: "border-color 0.15s",
      }}
    >
      {selected && (
        <span
          style={{
            position: "absolute",
            top: 10,
            right: 10,
            background: accentColor,
            color: "#fff",
            fontSize: 10,
            fontWeight: 700,
            padding: "2px 7px",
            borderRadius: 8,
          }}
        >
          Selected
        </span>
      )}
      <div style={{ color: accentColor, marginBottom: 8 }}>
        {isBlind ? <EyeOffIcon /> : <EyeIcon />}
      </div>
      <p style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 700, color: "#111827" }}>
        {isBlind ? "Blind" : "Omniscient"}
      </p>
      <p style={{ margin: 0, fontSize: 12, color: "#6b7280", lineHeight: 1.5 }}>
        {isBlind
          ? "See offer positions and your own utility only. Employer's preferences stay hidden."
          : "See all indifference curves, the employer's belief, and both Nash points in real time."}
      </p>
    </button>
  );
}
