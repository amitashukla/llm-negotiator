interface RuleCardProps {
  icon: string;
  title: string;
  description: string;
}

export default function RuleCard({ icon, title, description }: RuleCardProps) {
  return (
    <div
      style={{
        background: "#f9fafb",
        border: "1px solid #e5e7eb",
        borderRadius: 10,
        padding: "1rem",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <span style={{ fontSize: 22 }}>{icon}</span>
      <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "#111827" }}>{title}</p>
      <p style={{ margin: 0, fontSize: 12, color: "#6b7280", lineHeight: 1.5 }}>{description}</p>
    </div>
  );
}
