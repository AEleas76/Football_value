"""Football value API.  Run from the project root:
    uvicorn api.main:app --reload
Docs (auto-generated):  http://127.0.0.1:8000/docs
Needs api/predictions.json (export_predictions.py) and api/stats.json (export_stats.py).
"""
import json, unicodedata
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE = Path(__file__).parent

def _load(name: str):
    with open(BASE / name, encoding="utf-8") as f:
        return json.load(f)

_pred, _stats = _load("predictions.json"), _load("stats.json")
META, PLAYERS = _pred["meta"], _pred["players"]
SEASONS = _stats["seasons"]
HISTORY, LEADERBOARD = _stats["history"], _stats["leaderboard"]

# add photo, contract, birthplace... to every player record
for _p in PLAYERS:
    _p.update(_stats["profiles"].get(str(_p["player_id"]), {}))
BY_ID = {p["player_id"]: p for p in PLAYERS}

def _norm(s: str) -> str:
    """lowercase and strip accents so 'odegaard' finds 'Odegaard'-style names"""
    s = s.replace("ø", "o").replace("Ø", "O").replace("ß", "ss")
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))

SEARCH = {p["player_id"]: _norm(p["name"]) for p in PLAYERS}
LB_NORM = {season: [_norm(r["name"]) for r in rows] for season, rows in LEADERBOARD.items()}

def _summary(p: dict) -> dict:
    return {k: p.get(k) for k in ["player_id", "name", "club", "league", "position", "age", "image_url",
                                  "market_value", "predicted_value", "gap_pct"]}

app = FastAPI(title="Football Value Predictor API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
# allow_origins=["*"] is fine for a read-only public API; restrict it to your site's URL once deployed.

@app.get("/api/health")
def health():
    return {"status": "ok", **META, "seasons": SEASONS}

@app.get("/api/featured")
def featured(limit: int = Query(8, ge=1, le=24)):
    """most valuable players of the latest season"""
    return [_summary(p) for p in sorted(PLAYERS, key=lambda p: -p["market_value"])[:limit]]

@app.get("/api/players/search")
def search(q: str = Query(..., min_length=2), limit: int = Query(10, ge=1, le=50)):
    terms = _norm(q).split()
    hits = [p for p in PLAYERS if all(t in SEARCH[p["player_id"]] for t in terms)]
    hits.sort(key=lambda p: -p["market_value"])          # most valuable first
    return [_summary(p) for p in hits[:limit]]

@app.get("/api/players/{player_id}")
def player(player_id: int):
    p = BY_ID.get(player_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Player not found (only players with 450+ minutes in the latest season)")
    return p

@app.get("/api/players/{player_id}/stats")
def player_stats(player_id: int):
    """last five seasons, all competitions, with a breakdown by competition"""
    p = BY_ID.get(player_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"player_id": player_id, "name": p["name"], "seasons": HISTORY.get(str(player_id), [])}

@app.get("/api/compare")
def compare(a: int, b: int):
    pa, pb = BY_ID.get(a), BY_ID.get(b)
    if pa is None or pb is None:
        raise HTTPException(status_code=404, detail="One of the players was not found")
    return {"a": pa, "b": pb}

@app.get("/api/gaps")
def gaps(direction: str = Query("under", pattern="^(under|over)$"),
         position: str | None = None, league: str | None = None,
         min_minutes: int = Query(900, ge=0), min_value: int = Query(10_000_000, ge=0),
         limit: int = Query(20, ge=1, le=100)):
    """Clearest disagreements between model and market.
    under: market value is BELOW the model's 80% range.  over: market value is ABOVE it.
    Ranked by the size of the gap in euros."""
    rows = []
    for p in PLAYERS:
        if not p["stats"]["minutes"] or p["stats"]["minutes"] < min_minutes or p["market_value"] < min_value:
            continue
        if position and p["position"] != position:
            continue
        if league and p["league"] != league:
            continue
        if direction == "under" and not p["market_value"] < p["range_low"]:
            continue
        if direction == "over" and not p["market_value"] > p["range_high"]:
            continue
        rows.append(p)
    rows.sort(key=lambda p: abs(p["predicted_value"] - p["market_value"]), reverse=True)
    return [_summary(p) for p in rows[:limit]]

@app.get("/api/seasons/{season}/leaders")
def leaders(season: int, position: str | None = None, league: str | None = None, q: str | None = None,
            sort: str = Query("ga", pattern="^(goals|assists|ga|ga_p90|minutes|market_value)$"),
            min_minutes: int = Query(450, ge=0), limit: int = Query(50, ge=1, le=200)):
    """season leaderboard (top-5-league players with 450+ minutes), searchable by name"""
    rows = LEADERBOARD.get(str(season))
    if rows is None:
        raise HTTPException(status_code=404, detail=f"No data for season {season}")
    terms = _norm(q).split() if q else []
    keep = []
    for r, name in zip(rows, LB_NORM[str(season)]):
        if r["minutes"] < min_minutes:
            continue
        if position and r["position"] != position:
            continue
        if league and r["league"] != league:
            continue
        if terms and not all(t in name for t in terms):
            continue
        keep.append({**r, "ga": r["goals"] + r["assists"]})
    keep.sort(key=lambda r: -(r[sort] if r[sort] is not None else -1))
    return {"season": season, "total": len(keep), "rows": keep[:limit]}