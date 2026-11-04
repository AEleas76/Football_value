// Where the FastAPI service lives. Override with VITE_API_URL (see .env.example).
const BASE = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

async function get(path, params = {}, signal) {
  const url = new URL(BASE + path);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  let res;
  try {
    res = await fetch(url, { signal });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new Error("Cannot reach the API. Is it running? (uvicorn api.main:app --reload)");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* body was not JSON */
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return res.json();
}

export const getHealth = (signal) => get("/api/health", {}, signal);
export const searchPlayers = (q, signal) => get("/api/players/search", { q, limit: 8 }, signal);
export const getPlayer = (id, signal) => get(`/api/players/${id}`, {}, signal);
export const comparePlayers = (a, b, signal) => get("/api/compare", { a, b }, signal);
export const getGaps = (params, signal) => get("/api/gaps", params, signal);
export const getFeatured = (limit, signal) => get("/api/featured", { limit }, signal);
export const getPlayerStats = (id, signal) => get(`/api/players/${id}/stats`, {}, signal);
export const getLeaders = (season, params, signal) => get(`/api/seasons/${season}/leaders`, params, signal);
