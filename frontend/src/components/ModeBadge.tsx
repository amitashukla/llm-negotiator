import type { GameMode } from "../types";

interface ModeBadgeProps {
  mode: GameMode;
}

export default function ModeBadge({ mode }: ModeBadgeProps) {
  const isOmniscient = mode === "omniscient";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: 12,
        fontSize: 12,
        fontWeight: 600,
        background: isOmniscient ? "#EEEDFE" : "#f3f4f6",
        color: isOmniscient ? "#534AB7" : "#6b7280",
        border: `1px solid ${isOmniscient ? "#c4c0f5" : "#e5e7eb"}`,
        whiteSpace: "nowrap",
      }}
    >
      {isOmniscient ? "Omniscient" : "Blind"}
    </span>
  );
}
