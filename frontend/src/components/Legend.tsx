import type { GameMode } from "../types";

interface LegendRowProps {
  sample: React.ReactNode;
  label: string;
}

function Row({ sample, label }: LegendRowProps) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
      <div style={{ width: 28, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {sample}
      </div>
      <span style={{ fontSize: 11, color: "#6b7280" }}>{label}</span>
    </div>
  );
}

function DotSample({ fill, stroke }: { fill: string; stroke: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14">
      <circle cx="7" cy="7" r="5" fill={fill} stroke={stroke} strokeWidth="1.5" />
    </svg>
  );
}

function LineSample({ stroke, dasharray }: { stroke: string; dasharray?: string }) {
  return (
    <svg width="28" height="10" viewBox="0 0 28 10">
      <line x1="0" y1="5" x2="28" y2="5" stroke={stroke} strokeWidth="2" strokeDasharray={dasharray ?? "none"} />
    </svg>
  );
}

function CrossSample({ color }: { color: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14">
      <line x1="2" y1="2" x2="12" y2="12" stroke={color} strokeWidth="2.5" />
      <line x1="12" y1="2" x2="2" y2="12" stroke={color} strokeWidth="2.5" />
    </svg>
  );
}

function LensRegionSample({ color }: { color: string }) {
  return (
    <svg width="22" height="12" viewBox="0 0 22 12">
      <ellipse cx="11" cy="6" rx="10" ry="5" fill={color} fillOpacity={0.25} stroke={color} strokeWidth="1" strokeOpacity={0.7} />
    </svg>
  );
}

type LegendMode = GameMode | "reveal";

interface LegendProps {
  mode: LegendMode;
}

export default function Legend({ mode }: LegendProps) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e5e7eb",
        borderRadius: 10,
        padding: "0.875rem 1rem",
      }}
    >
      <p style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 600, color: "#374151" }}>Legend</p>

      <Row
        sample={<DotSample fill="#C0DD97" stroke="#639922" />}
        label="Your offer (C1, C2…)"
      />
      <Row
        sample={<DotSample fill="#B5D4F4" stroke="#378ADD" />}
        label="Employer offer (E1, E2…)"
      />
      <Row
        sample={<DotSample fill="#C0DD97" stroke="#639922" />}
        label="Most recent offer (larger)"
      />
      <Row
        sample={<LineSample stroke="#9FE1CB" dasharray="4,3" />}
        label="Offer path"
      />
      <Row
        sample={
          <svg width="14" height="14" viewBox="0 0 14 14">
            <line x1="3" y1="7" x2="11" y2="7" stroke="#AFA9EC" strokeWidth="2" />
            <line x1="7" y1="3" x2="7" y2="11" stroke="#AFA9EC" strokeWidth="2" />
          </svg>
        }
        label="Endowment point"
      />

      {(mode === "omniscient" || mode === "reveal") && (
        <>
          <Row
            sample={<LineSample stroke="#639922" />}
            label="Your indiff. curve (true)"
          />
          <Row
            sample={<LineSample stroke="#D85A30" />}
            label="Employer indiff. curve (true)"
          />
          <Row
            sample={<CrossSample color="#2C2C2A" />}
            label="True Nash (Nash*)"
          />
          <Row
            sample={<DotSample fill="#639922" stroke="#639922" />}
            label="Employer Nash guess (Nasĥ)"
          />
        </>
      )}

      {mode === "omniscient" && (
        <Row
          sample={<LineSample stroke="#7F77DD" dasharray="5,3" />}
          label="Employer believed indiff. curve"
        />
      )}

      {mode === "reveal" && (
        <Row
          sample={<LensRegionSample color="#9FE1CB" />}
          label="True lens (mutual gains region)"
        />
      )}
    </div>
  );
}
