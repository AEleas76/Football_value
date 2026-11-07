"""Fetches CURRENT stats (and transfers) from API-Football and writes data/live/*.csv, which export_stats.py and
export_predictions.py merge on top of the frozen Transfermarkt dataset.

  one-time:   create a free key at https://dashboard.api-football.com  and set it:   setx APIFOOTBALL_KEY "your-key"
  test it:    python update_live.py --check
  run:        python update_live.py --max-requests 90          (re-run daily: it resumes where it stopped)
  extras:     --world-cup   fetch the whole 2026 World Cup (counted in 2025/26)     --transfers   fetch summer moves
              --cups        also fetch the domestic cups

Free plan = 100 requests/day, so a full refresh takes a few days; results are cached in data/live/cache.
"""
import argparse, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd

BASE = "https://v3.football.api-sports.io"
DATA = Path("data")
LIVE, CACHE = DATA / "live", DATA / "live" / "cache"

# (API-Football league id, name used on the website, kind)
LEAGUES = [(39, "Premier League", "League"), (140, "LaLiga", "League"), (78, "Bundesliga", "League"),
           (135, "Serie A", "League"), (61, "Ligue 1", "League")]
EUROPE = [(2, "Champions League", "Europe"), (3, "Europa League", "Europe")]
CUPS = [(45, "FA Cup", "Cup"), (48, "EFL Cup", "Cup"), (143, "Copa del Rey", "Cup"), (81, "DFB-Pokal", "Cup"),
        (137, "Coppa Italia", "Cup"), (66, "Coupe de France", "Cup")]
WORLD_CUP = (1, "World Cup", "International")      # API season 2026 -> counted in the 2025/26 season on the site

class OutOfBudget(Exception):
    """raised when today's request allowance is used up"""

class Budget:
    def __init__(self, n): self.left = n
    def spend(self):
        if self.left <= 0: raise OutOfBudget()
        self.left -= 1

# ---------------------------------------------------------------- HTTP
def api_get(path, params, key=None):
    key = key or os.environ.get("APIFOOTBALL_KEY")
    if not key:
        sys.exit("Set your key first:  setx APIFOOTBALL_KEY \"your-key\"   (then open a NEW terminal)")
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"x-apisports-key": key}), timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from API-Football for {path}") from e
    if data.get("errors"):                           # e.g. plan does not include this season
        raise RuntimeError(f"API-Football refused the request: {data['errors']}")
    return data

def cached(name, loader, budget, fresh_days):
    """read data/live/cache/<name>.json if it is recent enough, otherwise fetch (and spend one request)"""
    f = CACHE / f"{name}.json"
    if f.exists() and (time.time() - f.stat().st_mtime) < fresh_days * 86400:
        return json.load(open(f, encoding="utf-8"))
    budget.spend()
    data = loader()
    CACHE.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(f, "w", encoding="utf-8"))
    return data

# ---------------------------------------------------------------- name matching
STOP = {"fc", "cf", "afc", "sc", "ac", "as", "ssc", "us", "rc", "rcd", "ud", "ca", "cd", "sv", "vfl", "vfb", "tsg", "fsv",
        "football", "club", "calcio", "association", "de", "del", "la", "of", "the", "and", "1", "04", "05", "09", "1846", "1899", "1907"}

def tokens(text, drop_stop=False):
    t = unicodedata.normalize("NFKD", str(text).replace("ø", "o").replace("Ø", "O").replace("ß", "ss"))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    toks = re.findall(r"[a-z0-9]+", t)
    return [x for x in toks if x not in STOP] if drop_stop else toks

def match_players(api_rows, tm):
    """api_rows: dicts with api_id, name, firstname, lastname, dob.  tm: players.csv frame. Returns {api_id: tm_player_id}."""
    by_dob = defaultdict(list)
    for r in tm.dropna(subset=["date_of_birth"]).itertuples():
        by_dob[str(r.date_of_birth)[:10]].append((int(r.player_id), set(tokens(r.name)), tokens(r.name)[-1:] ))
    out, unmatched = {}, {}
    for r in {x["api_id"]: x for x in api_rows}.values():
        cands = by_dob.get(str(r["dob"])[:10], [])
        api_tok = set(tokens(f"{r.get('firstname') or ''} {r.get('lastname') or ''} {r['name']}"))
        best, best_score, tie = None, 0.0, False
        for pid, tm_tok, last in cands:
            inter = len(api_tok & tm_tok)
            score = inter / max(len(tm_tok), 1)
            if last and last[0] in api_tok: score = max(score, 0.75 + 0.25 * inter / max(len(tm_tok), 1))
            if score > best_score + 1e-9: best, best_score, tie = pid, score, False
            elif abs(score - best_score) < 1e-9 and score > 0: tie = True
        if best is not None and best_score >= 0.5 and not tie:
            out[r["api_id"]] = best
        else:
            unmatched[r["api_id"]] = r["name"]
    return out, unmatched

def club_key(name):
    return set(tokens(name, drop_stop=True))

def match_club(api_name, clubs, aliases):
    """api club name -> (tm_club_id, tm_club_name) or None"""
    if api_name in aliases:
        cid = aliases[api_name]
        return cid, clubs.loc[clubs.club_id == cid, "name"].iloc[0] if (clubs.club_id == cid).any() else api_name
    a = club_key(api_name)
    best, best_score = None, 0.0
    for c in clubs.itertuples():
        b = club_key(c.name)
        if not a or not b: continue
        if a == b: score = 1.0
        elif a <= b or b <= a: score = 0.9 - 0.02 * abs(len(a) - len(b))
        else: score = SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio()
        if score > best_score: best, best_score = c, score
    return (int(best.club_id), best.name) if best is not None and best_score >= 0.8 else None

# ---------------------------------------------------------------- parsing
def parse_players_page(page, league_id, comp, kind, site_season):
    for item in page.get("response", []):
        p = item["player"]
        for st in item.get("statistics", []):
            if st["league"]["id"] != league_id: continue
            g, goals, cards = st.get("games") or {}, st.get("goals") or {}, st.get("cards") or {}
            apps, minutes = g.get("appearences") or 0, g.get("minutes") or 0     # (sic) the API spells it "appearences"
            if apps == 0 and minutes == 0: continue
            yield {"api_id": p["id"], "name": p["name"], "firstname": p.get("firstname"), "lastname": p.get("lastname"),
                   "dob": (p.get("birth") or {}).get("date"), "team": st["team"]["name"], "team_id": st["team"]["id"],
                   "competition": comp, "kind": kind, "season": site_season, "apps": apps, "minutes": minutes,
                   "goals": goals.get("total") or 0, "assists": goals.get("assists") or 0,
                   "yellows": cards.get("yellow") or 0, "reds": (cards.get("red") or 0) + (cards.get("yellowred") or 0)}

def parse_fee(kind_text):
    """'€ 63.6M' -> 63600000, '€ 800K' -> 800000, 'Free' / 'N/A' -> 0, None for loans"""
    t = (kind_text or "").strip().lower()
    if "loan" in t: return None
    m = re.search(r"([\d.,]+)\s*([mk]?)", t)
    if not m or "€" not in t: return 0
    raw = m.group(1)
    if "," in raw and "." not in raw and raw.count(",") == 1 and len(raw.split(",")[1]) <= 2:
        raw = raw.replace(",", ".")                                  # decimal comma: "1,5"
    num = float(raw.replace(",", ""))
    return int(num * {"m": 1e6, "k": 1e3, "": 1}[m.group(2)])

# ---------------------------------------------------------------- main routine
def run(args, fetch=api_get):
    LIVE.mkdir(parents=True, exist_ok=True)
    budget = Budget(args.max_requests)
    comps = [(lid, n, k, args.season, args.season) for lid, n, k in LEAGUES + EUROPE + (CUPS if args.cups else [])]
    if args.world_cup:
        comps.append((WORLD_CUP[0], WORLD_CUP[1], WORLD_CUP[2], 2026, 2025))   # API season 2026 -> site season 2025
    rows, coverage = [], {}
    try:
        for lid, name, kind, api_season, site_season in comps:
            page, total = 1, 1
            while page <= total:
                data = cached(f"players_{lid}_{api_season}_{page}", lambda: fetch("/players", {"league": lid, "season": api_season, "page": page}), budget,
                              3650 if lid == WORLD_CUP[0] else args.fresh_days)   # the World Cup is over: fetch it once
                total = data.get("paging", {}).get("total", 1) or 1
                rows += list(parse_players_page(data, lid, name, kind, site_season))
                coverage[name] = f"{page}/{total} pages"
                page += 1
    except OutOfBudget:
        print("Request budget used up for today: run the script again tomorrow and it will continue.")
    print("coverage:", coverage)
    if not rows:
        print("Nothing fetched yet."); return

    tm = pd.read_csv(DATA / "players.csv", usecols=["player_id", "name", "date_of_birth", "last_season"])
    tm = tm[tm.last_season >= 2024]
    clubs = pd.read_csv(DATA / "clubs.csv", usecols=["club_id", "name"])
    alias_file = LIVE / "club_aliases.csv"
    aliases = dict(pd.read_csv(alias_file).values) if alias_file.exists() else {}
    id_map, unmatched = match_players(rows, tm)
    print(f"players matched to Transfermarkt: {len(id_map)} | not matched: {len(unmatched)}")
    pd.DataFrame(sorted(unmatched.items()), columns=["api_id", "name"]).to_csv(LIVE / "unmatched_players.csv", index=False)

    df = pd.DataFrame([r for r in rows if r["api_id"] in id_map])
    df["player_id"] = df.api_id.map(id_map)
    club_cache = {}
    def tm_club(n):
        if n not in club_cache: club_cache[n] = match_club(n, clubs, aliases)
        return club_cache[n]
    # one row per player / season / competition; a player who changed club mid-season is summed, club = where he played most
    keys = ["player_id", "season", "competition", "kind"]
    top = df.sort_values("minutes").groupby(keys, as_index=False).last()[keys + ["team"]]
    agg = df.groupby(keys, as_index=False)[["apps", "minutes", "goals", "assists", "yellows", "reds"]].sum().merge(top, on=keys)
    agg["club"] = [(tm_club(t) or (None, t))[1] for t in agg.team]
    unmatched_clubs = sorted({t for t in agg.team if tm_club(t) is None})
    if unmatched_clubs:
        print("clubs not matched (shown under their API name; add them to data/live/club_aliases.csv):", unmatched_clubs[:15])
    agg.drop(columns="team")[["player_id", "season", "competition", "kind", "club", "apps", "minutes", "goals", "assists", "yellows", "reds"]] \
        .to_csv(LIVE / "live_stats.csv", index=False)

    if args.transfers:
        fetch_moves(df, id_map, clubs, aliases, budget, fetch, args)
    meta = {"as_of": date.today().isoformat(), "source": "api-football", "coverage": coverage,
            "season": args.season, "players": int(agg.player_id.nunique())}
    json.dump(meta, open(LIVE / "live_meta.json", "w"))
    print(f"wrote {len(agg)} rows to {LIVE / 'live_stats.csv'}")

def fetch_moves(df, id_map, clubs, aliases, budget, fetch, args):
    """summer-window transfers for every club that appears in the five leagues"""
    league_names = {n for _, n, k in LEAGUES}
    team_ids = sorted(df[df.competition.isin(league_names)].team_id.unique())
    since = pd.Timestamp(args.moves_since)
    rows = []
    try:
        for tid in team_ids:
            data = cached(f"transfers_{tid}", lambda: fetch("/transfers", {"team": int(tid)}), budget, args.fresh_days)
            for item in data.get("response", []):
                pid = id_map.get(item["player"]["id"])
                if pid is None: continue
                for t in item.get("transfers", []):
                    d, fee = pd.Timestamp(t["date"]), parse_fee(t.get("type"))
                    if d < since or fee is None: continue                    # skip old moves and loans
                    to, out = t["teams"]["in"], t["teams"]["out"]
                    c_in, c_out = match_club(to["name"], clubs, aliases), match_club(out["name"], clubs, aliases)
                    if c_in is None: continue
                    rows.append({"player_id": pid, "transfer_date": d.date().isoformat(), "from_club_id": c_out[0] if c_out else -1,
                                 "to_club_id": c_in[0], "transfer_fee": fee, "to_club_name": c_in[1]})
    except OutOfBudget:
        print("Request budget used up while fetching transfers: run again tomorrow.")
    pd.DataFrame(rows).drop_duplicates(["player_id", "to_club_id", "transfer_date"]).to_csv(LIVE / "live_moves.csv", index=False)
    print(f"wrote {len(rows)} summer moves to {LIVE / 'live_moves.csv'}")

def check():
    key = os.environ.get("APIFOOTBALL_KEY")
    st = api_get("/status", {}, key)["response"]
    print("account:", st.get("account", {}).get("email"), "| plan:", st.get("subscription", {}).get("plan"),
          "| requests today:", st.get("requests", {}).get("current"), "/", st.get("requests", {}).get("limit_day"))
    season = date.today().year if date.today().month >= 7 else date.today().year - 1
    d = api_get("/players", {"league": 39, "season": season, "page": 1}, key)
    print(f"Premier League {season}: {d['paging']['total']} pages of players. First player:", d["response"][0]["player"]["name"])
    print("OK: your plan can read the current season.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="test the key and the plan, then stop")
    ap.add_argument("--season", type=int, default=date.today().year if date.today().month >= 7 else date.today().year - 1)
    ap.add_argument("--max-requests", type=int, default=90, help="stay under your daily quota (free plan: 100)")
    ap.add_argument("--fresh-days", type=float, default=6, help="re-use cached pages younger than this")
    ap.add_argument("--world-cup", action="store_true"); ap.add_argument("--cups", action="store_true")
    ap.add_argument("--transfers", action="store_true"); ap.add_argument("--moves-since", default="2026-07-01")
    a = ap.parse_args()
    check() if a.check else run(a)