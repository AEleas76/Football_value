export const LEAGUES = {
  GB1: "Premier League",
  ES1: "LaLiga",
  L1: "Bundesliga",
  IT1: "Serie A",
  FR1: "Ligue 1",
};

export const POSITIONS = ["Attack", "Midfield", "Defender", "Goalkeeper"];

// 12500000 -> "€12.5m", 150000000 -> "€150m", 450000 -> "€450k"
export function money(v) {
  if (v === null || v === undefined) return "–";
  if (v >= 1e6) {
    const m = v / 1e6;
    return `€${m >= 100 ? Math.round(m) : parseFloat(m.toFixed(1))}m`;
  }
  return `€${Math.round(v / 1e3)}k`;
}

// 2025 -> "2025/26"
export const seasonLabel = (s) => `${s}/${String((s + 1) % 100).padStart(2, "0")}`;

export function signedPct(v) {
  const r = Math.round(v);
  return `${r > 0 ? "+" : ""}${r}%`;
}

export function num(v, digits = 2) {
  return v === null || v === undefined ? "–" : Number(v).toFixed(digits);
}

// plain-English description of model vs market
export function gapText(gap) {
  if (Math.abs(gap) < 5) return "in line with the market value";
  return gap > 0
    ? `${Math.round(gap)}% above the market value`
    : `${Math.round(-gap)}% below the market value`;
}

export function gapClass(gap) {
  if (gap >= 15) return "up";
  if (gap <= -15) return "down";
  return "flat";
}

// a "nice" axis step for charts
export function niceStep(raw) {
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const m = raw / pow;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * pow;
}
