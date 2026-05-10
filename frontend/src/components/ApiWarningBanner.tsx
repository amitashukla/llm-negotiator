interface ApiWarningBannerProps {
  warnings: string[];
  onDismiss: () => void;
}

export default function ApiWarningBanner({ warnings, onDismiss }: ApiWarningBannerProps) {
  if (warnings.length === 0) return null;
  return (
    <div
      style={{
        background: "#fffbeb",
        border: "1px solid #f59e0b",
        borderRadius: 8,
        padding: "0.75rem 1rem",
        marginBottom: 16,
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
      }}
    >
      <span style={{ fontSize: 16, flexShrink: 0 }}>⚠️</span>
      <div style={{ flex: 1 }}>
        <p style={{ margin: "0 0 4px", fontSize: 13, fontWeight: 600, color: "#92400e" }}>
          Missing from API response
        </p>
        <p style={{ margin: 0, fontSize: 12, color: "#92400e" }}>
          {warnings.join(", ")}. Affected panels may show "—".
        </p>
      </div>
      <button
        onClick={onDismiss}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: 16,
          color: "#92400e",
          padding: 0,
          flexShrink: 0,
        }}
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}
