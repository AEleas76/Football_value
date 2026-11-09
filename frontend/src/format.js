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

// 2025 -> "2025/26", 2026 -> "2026/27 (Ongoing)"
export const seasonLabel = (s) => (s >= 2026 ? "2026/27 (Ongoing)" : `${s}/${String((s + 1) % 100).padStart(2, "0")}`);
// 2012 -> "12/13" (for crowded chart axes)
export const seasonShort = (s) => `${String(s % 100).padStart(2, "0")}/${String((s + 1) % 100).padStart(2, "0")}`;

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

// "Erling Haaland" -> "EH"
export function initials(name) {
  const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// "2028-06-30" -> "30 Jun 2028"
export function formatDate(iso) {
  if (!iso) return "–";
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

// age in whole years from "YYYY-MM-DD"
export function ageFrom(iso, now = new Date()) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  const month = now.getUTCMonth() + 1;
  let age = now.getUTCFullYear() - y;
  if (month < m || (month === m && now.getUTCDate() < d)) age -= 1;
  return age;
}

// time left on a contract: { text, tone } or null when unknown
export function contractLeft(iso, now = new Date()) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  let months = (y - now.getUTCFullYear()) * 12 + (m - (now.getUTCMonth() + 1));
  if (d < now.getUTCDate()) months -= 1;
  if (months < 0) return { text: "date passed", tone: "bad" };
  const years = Math.floor(months / 12);
  const rest = months % 12;
  const text = years > 0 ? `${years}y ${rest}m left` : `${rest}m left`;
  return { text, tone: months <= 12 ? "warn" : "ok" };
}

export const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

// Transfermarkt "header" thumbnails are small crops; the "big" version is the full portrait.
// Returns the URLs to try in order (the last one is always the original).
export function photoCandidates(url) {
  if (!url) return [];
  if (!url.includes("/portrait/header/")) return [url];
  const big = url.replace("/portrait/header/", "/portrait/big/");
  const list = [big];
  const asJpg = big.replace(/\.(png|jpeg|JPG)(\?|$)/, ".jpg$2");
  if (asJpg !== big) list.push(asJpg);
  list.push(url);
  return list;
}

// "2026-07" -> "Jul 2026"
export function monthLabel(ym) {
  if (!ym) return "–";
  return new Date(ym + "-01T00:00:00Z").toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
}
