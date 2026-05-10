export const W = 10;
export const H = 10;
export const EMPLOYER_BETA = 0.8;
export const ROUNDS = 5;
export const CANVAS = 420;
export const PAD = 48;
export const INNER = CANVAS - 2 * PAD;

export function toCanvas(xH: number, yH: number) {
  return { cx: PAD + (xH / W) * INNER, cy: PAD + ((H - yH) / H) * INNER };
}

export function fromCanvas(cx: number, cy: number) {
  return { xH: ((cx - PAD) / INNER) * W, yH: H - ((cy - PAD) / INNER) * H };
}

export function cobbDouglasUtility(x: number, y: number, alpha: number) {
  if (x <= 0 || y <= 0) return 0;
  return x ** alpha * y ** (1 - alpha);
}

export function offerUtilities(xH: number, yH: number, candidateAlpha: number) {
  const candidateU = cobbDouglasUtility(xH, yH, candidateAlpha);
  const employerX = W - xH;
  const employerY = H - yH;
  const employerU = cobbDouglasUtility(employerX, employerY, EMPLOYER_BETA);
  return { candidateU, employerU, employerX, employerY };
}

function candidateIcY(xC: number, alpha: number, utility: number): number | null {
  if (xC <= 0 || xC >= W) return null;
  const base = xC ** alpha;
  if (base === 0) return null;
  return (utility / base) ** (1 / (1 - alpha));
}

function employerIcY(xC: number, utility: number): number | null {
  if (xC <= 0 || xC >= W) return null;
  const employerX = W - xC;
  const base = employerX ** EMPLOYER_BETA;
  if (base === 0) return null;
  const employerY = (utility / base) ** (1 / (1 - EMPLOYER_BETA));
  return H - employerY;
}

export function buildIcPath(
  allocXH: number,
  allocYH: number,
  alpha: number,
  side: "candidate" | "employer"
): string | null {
  const candidateU = cobbDouglasUtility(allocXH, allocYH, alpha);
  const employerU = cobbDouglasUtility(W - allocXH, H - allocYH, EMPLOYER_BETA);
  const samples = 240;
  const pts: { xH: number; yH: number }[] = [];
  for (let i = 1; i < samples; i++) {
    const xC = (i / samples) * (W - 0.02) + 0.01;
    const y =
      side === "candidate"
        ? candidateIcY(xC, alpha, candidateU)
        : employerIcY(xC, employerU);
    if (y !== null && y >= 0 && y <= H) {
      pts.push({ xH: xC, yH: y });
    }
  }
  if (pts.length < 2) return null;
  return pts
    .map((p, i) => {
      const c = toCanvas(p.xH, p.yH);
      return `${i === 0 ? "M" : "L"} ${c.cx.toFixed(2)} ${c.cy.toFixed(2)}`;
    })
    .join(" ");
}

export function buildLensPath(endowX: number, endowY: number, candidateAlpha: number): string | null {
  const uCEndow = cobbDouglasUtility(endowX, endowY, candidateAlpha);
  const uEEndow = cobbDouglasUtility(W - endowX, H - endowY, EMPLOYER_BETA);
  const samples = 300;
  const upperPts: { xH: number; yH: number }[] = [];
  const lowerPts: { xH: number; yH: number }[] = [];

  for (let i = 1; i < samples; i++) {
    const xC = (i / samples) * (W - 0.02) + 0.01;
    const yC = candidateIcY(xC, candidateAlpha, uCEndow);
    const yE = employerIcY(xC, uEEndow);
    if (yC === null || yE === null) continue;
    if (yC < 0 || yC > H || yE < 0 || yE > H) continue;
    if (yE > yC) {
      upperPts.push({ xH: xC, yH: yE });
      lowerPts.push({ xH: xC, yH: yC });
    }
  }

  if (upperPts.length < 2) return null;
  const allPts = [...upperPts, ...[...lowerPts].reverse()];
  return (
    allPts
      .map((p, i) => {
        const c = toCanvas(p.xH, p.yH);
        return `${i === 0 ? "M" : "L"} ${c.cx.toFixed(2)} ${c.cy.toFixed(2)}`;
      })
      .join(" ") + " Z"
  );
}
