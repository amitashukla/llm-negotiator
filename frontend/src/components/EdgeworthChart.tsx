import { useMemo, useRef } from "react";
import type { Offer } from "../types";
import {
  toCanvas,
  fromCanvas,
  buildIcPath,
  buildLensPath,
  CANVAS,
  PAD,
  INNER,
  W,
  H,
} from "../utils/curves";

export type ChartMode = "blind" | "omniscient" | "reveal";

const C = {
  candidateStroke: "#639922",
  candidateFill: "#C0DD97",
  employerStroke: "#378ADD",
  employerFill: "#B5D4F4",
  candidateCurve: "#639922",
  employerTrueCurve: "#D85A30",
  employerBelievedCurve: "#7F77DD",
  trueNash: "#2C2C2A",
  employerNashDot: "#639922",
  offerPath: "#9FE1CB",
  endowment: "#AFA9EC",
  lens: "#9FE1CB",
};

interface EdgeworthChartProps {
  mode: ChartMode;
  offers: Offer[];
  pendingPoint: { xH: number; yH: number } | null;
  endowment: { xH: number; yH: number };
  alpha: number | null;
  alphaHat: number;
  agreedOffer: Offer | null;
  trueNash: { xH: number; yH: number } | null;
  employerNash: { xH: number; yH: number } | null;
  isPlayerTurn: boolean;
  onChartClick: (x: number, y: number) => void;
}

export default function EdgeworthChart({
  mode,
  offers,
  pendingPoint,
  endowment,
  alpha,
  alphaHat,
  agreedOffer,
  trueNash,
  employerNash,
  isPlayerTurn,
  onChartClick,
}: EdgeworthChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const showCurves = mode === "omniscient" || mode === "reveal";
  const showBelievedCurve = mode === "omniscient";
  const showNash = mode === "omniscient" || mode === "reveal";
  const showLens = mode === "reveal";

  const candidateTrueIcPath = useMemo(
    () => (showCurves && alpha != null ? buildIcPath(endowment.xH, endowment.yH, alpha, "candidate") : null),
    [showCurves, alpha, endowment.xH, endowment.yH]
  );

  const employerTrueIcPath = useMemo(
    () => (showCurves ? buildIcPath(endowment.xH, endowment.yH, 0.8, "employer") : null),
    [showCurves, endowment.xH, endowment.yH]
  );

  const employerBelievedIcPath = useMemo(
    () => (showBelievedCurve ? buildIcPath(endowment.xH, endowment.yH, alphaHat, "candidate") : null),
    [showBelievedCurve, alphaHat, endowment.xH, endowment.yH]
  );

  const lensPath = useMemo(
    () => (showLens && alpha != null ? buildLensPath(endowment.xH, endowment.yH, alpha) : null),
    [showLens, alpha, endowment.xH, endowment.yH]
  );

  const agreedCandidateIcPath = useMemo(
    () =>
      mode === "reveal" && alpha != null && agreedOffer
        ? buildIcPath(agreedOffer.xH, agreedOffer.yH, alpha, "candidate")
        : null,
    [mode, alpha, agreedOffer]
  );

  const agreedEmployerIcPath = useMemo(
    () =>
      mode === "reveal" && agreedOffer
        ? buildIcPath(agreedOffer.xH, agreedOffer.yH, 0.8, "employer")
        : null,
    [mode, agreedOffer]
  );

  function handleClick(e: React.MouseEvent<SVGSVGElement>) {
    if (!isPlayerTurn) return;
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const sx = CANVAS / rect.width;
    const sy = CANVAS / rect.height;
    const { xH, yH } = fromCanvas(
      (e.clientX - rect.left) * sx,
      (e.clientY - rect.top) * sy
    );
    if (xH < 0 || xH > W || yH < 0 || yH > H) return;
    onChartClick(xH, yH);
  }

  const endowC = toCanvas(endowment.xH, endowment.yH);
  const mostRecentOffer = offers.length > 0 ? offers[offers.length - 1] : null;

  return (
    <svg
      ref={svgRef}
      width={CANVAS}
      height={CANVAS}
      viewBox={`0 0 ${CANVAS} ${CANVAS}`}
      style={{
        cursor: isPlayerTurn ? "crosshair" : "default",
        display: "block",
        maxWidth: "100%",
      }}
      onClick={handleClick}
    >
      {/* Box background */}
      <rect
        x={PAD}
        y={PAD}
        width={INNER}
        height={INNER}
        fill="#fff"
        stroke="#d1d5db"
        strokeWidth={1}
      />

      {/* Axis ticks and labels */}
      {[0, 2, 4, 6, 8, 10].map((v) => {
        const cx = PAD + (v / W) * INNER;
        const cy = PAD + ((H - v) / H) * INNER;
        return (
          <g key={v}>
            <line x1={cx} y1={PAD + INNER} x2={cx} y2={PAD + INNER + 4} stroke="#9ca3af" strokeWidth={1} />
            <text x={cx} y={PAD + INNER + 14} textAnchor="middle" fontSize={10} fill="#9ca3af">
              {v}
            </text>
            <line x1={PAD - 4} y1={cy} x2={PAD} y2={cy} stroke="#9ca3af" strokeWidth={1} />
            <text x={PAD - 8} y={cy + 4} textAnchor="end" fontSize={10} fill="#9ca3af">
              {v}
            </text>
          </g>
        );
      })}

      {/* Origin labels */}
      <text x={PAD + 2} y={PAD + INNER + 36} fontSize={11} fill="#6b7280">
        You ⊥
      </text>
      <text x={PAD + INNER - 2} y={PAD - 14} textAnchor="end" fontSize={11} fill="#6b7280">
        Employer ⊤
      </text>

      {/* Lens region (reveal only) */}
      {showLens && lensPath && (
        <path
          d={lensPath}
          fill={C.lens}
          fillOpacity={0.18}
          stroke={C.lens}
          strokeOpacity={0.55}
          strokeWidth={1}
        />
      )}

      {/* Candidate true IC through endowment (omniscient + reveal, solid green) */}
      {candidateTrueIcPath && (
        <path
          d={candidateTrueIcPath}
          fill="none"
          stroke={C.candidateCurve}
          strokeWidth={1.75}
          opacity={0.85}
        />
      )}

      {/* Employer true IC through endowment (omniscient + reveal, solid coral) */}
      {employerTrueIcPath && (
        <path
          d={employerTrueIcPath}
          fill="none"
          stroke={C.employerTrueCurve}
          strokeWidth={1.75}
          opacity={0.85}
        />
      )}

      {/* Employer believed IC through endowment (omniscient only, purple dashed) */}
      {employerBelievedIcPath && (
        <path
          d={employerBelievedIcPath}
          fill="none"
          stroke={C.employerBelievedCurve}
          strokeWidth={1.5}
          strokeDasharray="5,3"
          opacity={0.8}
        />
      )}

      {/* Dashed ICs through agreed/final allocation (reveal only) */}
      {agreedCandidateIcPath && (
        <path
          d={agreedCandidateIcPath}
          fill="none"
          stroke={C.candidateCurve}
          strokeWidth={1.5}
          strokeDasharray="7,4"
          opacity={0.65}
        />
      )}
      {agreedEmployerIcPath && (
        <path
          d={agreedEmployerIcPath}
          fill="none"
          stroke={C.employerTrueCurve}
          strokeWidth={1.5}
          strokeDasharray="7,4"
          opacity={0.65}
        />
      )}

      {/* Endowment crosshair (purple) */}
      <line
        x1={endowC.cx - 8}
        y1={endowC.cy}
        x2={endowC.cx + 8}
        y2={endowC.cy}
        stroke={C.endowment}
        strokeWidth={2}
      />
      <line
        x1={endowC.cx}
        y1={endowC.cy - 8}
        x2={endowC.cx}
        y2={endowC.cy + 8}
        stroke={C.endowment}
        strokeWidth={2}
      />
      <circle cx={endowC.cx} cy={endowC.cy} r={3} fill={C.endowment} />

      {/* Offer path lines and dots */}
      {offers.map((o, i) => {
        const c = toCanvas(o.xH, o.yH);
        const isCandidate = o.type === "candidate";
        const isLast = o === mostRecentOffer;
        const stroke = isCandidate ? C.candidateStroke : C.employerStroke;
        const fill = isCandidate ? C.candidateFill : C.employerFill;
        const r = isLast ? 8 : 5;
        const sw = isLast ? 2 : 1.5;
        return (
          <g key={`offer-${o.type}-${o.round}-${i}`}>
            {i > 0 && (() => {
              const prev = toCanvas(offers[i - 1].xH, offers[i - 1].yH);
              return (
                <line
                  x1={prev.cx}
                  y1={prev.cy}
                  x2={c.cx}
                  y2={c.cy}
                  stroke={C.offerPath}
                  strokeWidth={1.5}
                  strokeDasharray="4,3"
                />
              );
            })()}
            <circle cx={c.cx} cy={c.cy} r={r} fill={fill} stroke={stroke} strokeWidth={sw} opacity={0.92} />
            <text x={c.cx + r + 3} y={c.cy + 4} fontSize={10} fill={stroke} fontWeight={isLast ? 600 : 400}>
              {isCandidate ? "C" : "E"}
              {o.round}
            </text>
          </g>
        );
      })}

      {/* Pending point (faint dashed circle — shown while API call is in flight) */}
      {pendingPoint && (() => {
        const c = toCanvas(pendingPoint.xH, pendingPoint.yH);
        return (
          <circle
            cx={c.cx}
            cy={c.cy}
            r={9}
            fill="none"
            stroke="#9ca3af"
            strokeWidth={1.5}
            strokeDasharray="3,2"
            opacity={0.6}
          />
        );
      })()}

      {/* Agreed offer highlight ring */}
      {agreedOffer && (() => {
        const c = toCanvas(agreedOffer.xH, agreedOffer.yH);
        return (
          <>
            <circle cx={c.cx} cy={c.cy} r={12} fill="none" stroke="#1D9E75" strokeWidth={2} opacity={0.7} />
            <circle cx={c.cx} cy={c.cy} r={4} fill="#1D9E75" opacity={0.9} />
          </>
        );
      })()}

      {/* True Nash point × marker (omniscient + reveal) */}
      {showNash && trueNash && (() => {
        const c = toCanvas(trueNash.xH, trueNash.yH);
        return (
          <g>
            <line x1={c.cx - 7} y1={c.cy - 7} x2={c.cx + 7} y2={c.cy + 7} stroke={C.trueNash} strokeWidth={2.5} />
            <line x1={c.cx + 7} y1={c.cy - 7} x2={c.cx - 7} y2={c.cy + 7} stroke={C.trueNash} strokeWidth={2.5} />
            <text x={c.cx + 10} y={c.cy - 6} fontSize={10} fill={C.trueNash} fontWeight={700}>
              Nash*
            </text>
          </g>
        );
      })()}

      {/* Employer Nash guess dot (omniscient + reveal) */}
      {showNash && employerNash && (() => {
        const c = toCanvas(employerNash.xH, employerNash.yH);
        return (
          <g>
            <circle cx={c.cx} cy={c.cy} r={6} fill={C.employerNashDot} stroke="#fff" strokeWidth={1.5} />
            <text x={c.cx + 9} y={c.cy + 4} fontSize={10} fill={C.employerNashDot} fontWeight={700}>
              Nasĥ
            </text>
          </g>
        );
      })()}
    </svg>
  );
}
