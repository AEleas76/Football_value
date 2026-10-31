"""Football value API.  Run from the project root:
    uvicorn api.main:app --reload
Docs (auto-generated):  http://127.0.0.1:8000/docs
"""
import json, unicodedata
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE = Path(__file__).parent
with open(BASE / "predictions.json", encoding="utf-8") as f:
    _data = json.load(f)
META, PLAYERS = _data["meta"], _data["players"]
BY_ID = {p["player_id"]: p for p in PLAYERS}

def _norm(s: str) -> str:
    """lowercase and strip accents so 'odegaard' finds 'Ødegaard'-style names"""
    s = s.replace("ø", "o").replace("Ø", "O").replace("ß", "ss")
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))

SEARCH = {p["player_id"]: _norm(p["name"]) for p in PLAYERS}

def _summary(p: dict) -> dict:
    return {k: p[k] for k in ["player_id", "name", "club", "league", "position", "age",
                              "market_value", "predicted_value", "gap_pct"]}

app = FastAPI(title="Football Value Predictor API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
# allow_origins=["*"] is fine for a read-only public API; restrict it to your site's URL once deployed.

@app.get("/api/health")
def health():
    return {"status": "ok", **META}

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

@app.get("/api/compare")
def compare(a: int, b: int):
    pa, pb = BY_ID.get(a), BY_ID.get(b)
    if pa is None or pb is None:
        raise HTTPException(status_code=404, detail="One of the players was not found")
    return {"a": pa, "b": pb}

@app.get("/api/gaps")
def gaps(direction: str = Query("under", pattern="^(under|over)$"),
         position: str | None = None, league: str | None = None,
         min_minutes: int = Query(900, ge=0), min_value: int = Query(5_000_000, ge=0),
         limit: int = Query(20, ge=1, le=100)):
    """direction=under -> model value above market value; over -> model value below market value"""
    rows = [p for p in PLAYERS
            if p["stats"]["minutes"] and p["stats"]["minutes"] >= min_minutes
            and p["market_value"] >= min_value
            and (position is None or p["position"] == position)
            and (league is None or p["league"] == league)]
    rows.sort(key=lambda p: p["gap_pct"], reverse=(direction == "under"))
    return [_summary(p) for p in rows[:limit]]