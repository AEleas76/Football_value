"""Builds api/stats.json: player profiles (photo, contract...), 5-season statistics per
player (with a breakdown by competition) and a season leaderboard.
Run AFTER export_predictions.py, from the project root:  python export_stats.py
"""
import json
import numpy as np, pandas as pd
from pathlib import Path

DATA, API = Path("data"), Path("api")
feats = pd.read_csv(DATA / "features_v3.csv")
available_seasons = sorted(int(s) for s in feats.season.unique())
SEASONS = [s for s in available_seasons if s >= 2021]            # dynamic 5-year+ lookback

pred = json.load(open(API / "predictions.json", encoding="utf-8"))
ids = {p["player_id"] for p in pred["players"]}

players = pd.read_csv(DATA / "players.csv")
clubs = pd.read_csv(DATA / "clubs.csv")[["club_id", "name"]].rename(columns={"name": "club_name"})
games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season", "competition_id", "date"])
is_wc_2026 = (games.competition_id == "FIWC") & (pd.to_datetime(games.date).dt.year == 2026)
games.loc[is_wc_2026, "season"] = 2025
games = games[["game_id", "season"]]

apps = pd.read_csv(DATA / "appearances.csv",
                   usecols=["game_id", "player_id", "player_club_id", "competition_id",
                            "yellow_cards", "red_cards", "goals", "assists", "minutes_played"])

def clean(v):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return round(float(v), 3)
    return v

# ---------- 1. Profiles ----------
def iso(x):
    return None if pd.isna(x) else str(x)[:10]

profiles = {}
for r in players[players.player_id.isin(ids)].itertuples():
    profiles[int(r.player_id)] = {
        "image_url": None if pd.isna(r.image_url) else r.image_url,
        "profile_url": None if pd.isna(r.url) else r.url,
        "date_of_birth": iso(r.date_of_birth),
        "contract_expiration": iso(r.contract_expiration_date),
        "current_club": None if pd.isna(r.current_club_name) else r.current_club_name,
        "country_of_birth": None if pd.isna(r.country_of_birth) else r.country_of_birth,
        "city_of_birth": None if pd.isna(r.city_of_birth) else str(r.city_of_birth).strip(),
        "height_cm": None if pd.isna(r.height_in_cm) else int(r.height_in_cm),
        "foot": None if pd.isna(r.foot) else r.foot,
        "international_caps": None if pd.isna(r.international_caps) else int(r.international_caps),
        "international_goals": None if pd.isna(r.international_goals) else int(r.international_goals),
        "highest_market_value": None if pd.isna(r.highest_market_value_in_eur) else int(r.highest_market_value_in_eur),
    }

# ---------- 2. Per-player, per-season, per-competition stats (all clubs, all competitions) ----------
a = apps.merge(games, on="game_id", how="inner")
a = a[a.season.isin(SEASONS)]
PRETTY = {
    "uefa-champions-league": "Champions League", "uefa-europa-league": "Europa League",
    "uefa-conference-league": "Conference League", "uefa-super-cup": "UEFA Super Cup",
    "uefa-champions-league-qualifying": "Champions League qualifying",
    "uefa-europa-league-qualifying": "Europa League qualifying",
    "uefa-conference-league-qualifying": "Conference League qualifying",
    "premier-league": "Premier League", "laliga": "LaLiga", "bundesliga": "Bundesliga",
    "serie-a": "Serie A", "ligue-1": "Ligue 1", "copa-del-rey": "Copa del Rey",
    "dfb-pokal": "DFB-Pokal", "italy-cup": "Coppa Italia", "fa-cup": "FA Cup",
    "world-cup": "World Cup", "africa-cup-of-nations": "Africa Cup of Nations",
    "liga-portugal": "Liga Portugal", "eredivisie": "Eredivisie", "super-lig": "Super Lig",
    "jupiler-pro-league": "Jupiler Pro League", "community-shield": "Community Shield",
    "franz-beckenbauer-supercup": "DFL-Supercup", "supercoppa-italiana": "Supercoppa Italiana",
    "supercopa": "Supercopa de Espana", "trophee-des-champions": "Trophee des Champions",
}
# competition ids that are used in matches but missing from competitions.csv
EXTRA = {"CGB": ("EFL Cup", "Cup"), "POCP": ("Taca de Portugal", "Cup"),
         "KLUB": ("Club World Cup", "Other"), "UKRS": ("Ukrainian Super Cup", "Cup")}

def describe(row):
    name = PRETTY.get(row["name"], str(row["name"]).replace("-", " ").title())
    if row["name"] not in PRETTY and isinstance(row["country_name"], str):
        name = f"{name} ({row['country_name']})"          # e.g. Premier Liga (Russia) vs (Ukraine)
    sub, typ = str(row["sub_type"]), row["type"]
    if typ == "domestic_league" or sub == "play_off": k = "League"
    elif typ == "domestic_cup" or sub == "domestic_super_cup": k = "Cup"
    elif sub.startswith("uefa") and "euro" not in sub.split("_")[:2]: k = "Europe"
    elif typ == "national_team_competition": k = "International"
    else: k = "Other"
    return pd.Series({"pretty": name, "kind": k})

comps_full = pd.read_csv(DATA / "competitions.csv")[["competition_id", "name", "type", "sub_type", "country_name"]]
comps = pd.concat([comps_full[["competition_id"]], comps_full.apply(describe, axis=1)], axis=1)
comps = pd.concat([comps, pd.DataFrame([{"competition_id": k, "pretty": v[0], "kind": v[1]} for k, v in EXTRA.items()])])

by_comp_base = None
mine = a[a.player_id.isin(ids)]
by_comp = (mine.groupby(["player_id", "season", "competition_id"], as_index=False)
           .agg(apps=("game_id", "count"), minutes=("minutes_played", "sum"), goals=("goals", "sum"),
                assists=("assists", "sum"), yellows=("yellow_cards", "sum"), reds=("red_cards", "sum"))
           .merge(comps[["competition_id", "pretty", "kind"]], on="competition_id", how="left"))
by_comp["pretty"] = by_comp.pretty.fillna(by_comp.competition_id)
by_comp["kind"] = by_comp.kind.fillna("Other")

main_club = (mine.groupby(["player_id", "season", "player_club_id"], as_index=False).minutes_played.sum()
             .sort_values("minutes_played").groupby(["player_id", "season"], as_index=False).last()
             .merge(clubs, left_on="player_club_id", right_on="club_id", how="left")[["player_id", "season", "club_name"]])
mv = feats[["player_id", "season", "market_value"]]

history = {}
for (pid, season), g in by_comp.groupby(["player_id", "season"]):
    g = g.sort_values("minutes", ascending=False)
    tot = g[["apps", "minutes", "goals", "assists", "yellows", "reds"]].sum()
    history.setdefault(int(pid), []).append({
        "season": int(season),
        **{k: int(v) for k, v in tot.items()},
        "ga_p90": clean(round((tot.goals + tot.assists) / tot.minutes * 90, 2)) if tot.minutes >= 270 else None,
        "competitions": [{"name": r.pretty, "kind": r.kind, "apps": int(r.apps), "minutes": int(r.minutes),
                          "goals": int(r.goals), "assists": int(r.assists),
                          "yellows": int(r.yellows), "reds": int(r.reds)} for r in g.itertuples()],
    })
meta_rows = main_club.merge(mv, on=["player_id", "season"], how="left").set_index(["player_id", "season"])
for pid, rows in history.items():
    rows.sort(key=lambda r: r["season"])
    for r in rows:
        key = (pid, r["season"])
        r["club"] = meta_rows.club_name.get(key) if key in meta_rows.index else None
        v = meta_rows.market_value.get(key) if key in meta_rows.index else None
        r["market_value"] = None if v is None or pd.isna(v) else int(v)

# ---------- 3. Season leaderboard (top-5-league players with 450+ minutes) ----------
f = feats[feats.season.isin(SEASONS)].merge(clubs, on="club_id", how="left")
leaderboard = {}
for season, g in f.groupby("season"):
    leaderboard[str(int(season))] = [{
        "player_id": int(r.player_id), "name": r.name, "club": r.club_name, "league": r.league,
        "position": r.position, "age": round(float(r.age), 1), "minutes": int(r.minutes), "apps": int(r.apps),
        "goals": int(r.goals), "assists": int(r.assists), "yellows": int(r.yellows), "reds": int(r.reds),
        "ga_p90": clean(round(float(r.ga_p90), 2)) if pd.notna(r.ga_p90) else None,
        "market_value": int(r.market_value), "has_profile": int(r.player_id) in ids,
    } for r in g.itertuples()]

out = {"seasons": SEASONS, "profiles": profiles, "history": history, "leaderboard": leaderboard}
with open(API / "stats.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))

print(f"profiles: {len(profiles)} | players with history: {len(history)} | "
      f"leaderboard rows: {sum(len(v) for v in leaderboard.values())}")
print(f"api/stats.json = {(API / 'stats.json').stat().st_size / 1e6:.1f} MB")
print("seasons per player (count of players):", pd.Series([len(v) for v in history.values()]).value_counts().sort_index().to_dict())
missing = [p["name"] for p in pred["players"] if p["player_id"] not in history][:5]
print("players with no stats at all:", len([p for p in pred["players"] if p["player_id"] not in history]), missing)
hid = next(p["player_id"] for p in pred["players"] if p["name"] == "Erling Haaland")
print("\nHaaland profile:", json.dumps(profiles[hid], ensure_ascii=False))
for r in history[hid]:
    print(r["season"], r["club"], r["apps"], "apps", r["minutes"], "min", r["goals"], "g", r["assists"], "a", r["ga_p90"], "mv", r["market_value"],
          "|", ", ".join(f'{c["name"]} {c["goals"]}g' for c in r["competitions"]))