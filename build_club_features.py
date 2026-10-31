"""Adds club-strength features to features_v1.csv and writes features_v2.csv.
Run from the project root:  python build_club_features.py
"""
import pandas as pd, numpy as np
from pathlib import Path

DATA = Path("data")
df    = pd.read_csv(DATA / "features_v1.csv", parse_dates=["valuation_date"])
vals  = pd.read_csv(DATA / "player_valuations.csv", parse_dates=["date"])
games = pd.read_csv(DATA / "games.csv", parse_dates=["date"])

# ---------- 0. Data-quality fix: keep only clubs that really played in a top-5 league that season ----------
# The valuation file's league label is not always the league of that season (e.g. a club later promoted
# gets labelled Ligue 1 even for years it was in Ligue 2). We take the league from the matches instead.
TOP5 = ["GB1", "ES1", "L1", "IT1", "FR1"]
lg5 = games[games.competition_id.isin(TOP5)]
played = pd.concat([
    lg5[["season", "home_club_id", "competition_id"]].set_axis(["season", "club_id", "league_real"], axis=1),
    lg5[["season", "away_club_id", "competition_id"]].set_axis(["season", "club_id", "league_real"], axis=1)])
played = (played.groupby(["club_id", "season", "league_real"]).size().rename("n_games").reset_index()
          .sort_values("n_games").groupby(["club_id", "season"], as_index=False).last())
played = played[played.n_games >= 10][["club_id", "season", "league_real"]]
n_before = len(df)
df = df.merge(played, on=["club_id", "season"], how="inner")
df["league"] = df.league_real
df = df.drop(columns="league_real")
print(f"Dropped {n_before - len(df)} rows from clubs that were not in a top-5 league that season")

# ---------- 1. Squad value of each club (excluding the player himself) ----------
# For season S we take every player's latest valuation on or before 1 Jan (S+1),
# no older than 12 months, and sum them per club. Season-by-season, no use of today's values.
rows = []
for s in sorted(df.season.unique()):
    cutoff = pd.Timestamp(year=s + 1, month=1, day=1)
    snap = vals[(vals.date <= cutoff) & (vals.date >= cutoff - pd.Timedelta(days=365))]
    snap = snap.sort_values("date").groupby("player_id", as_index=False).last()
    snap = snap[["player_id", "current_club_id", "market_value_in_eur"]]
    snap.columns = ["player_id", "club_id", "snap_value"]
    snap["season"] = s
    rows.append(snap)
snap = pd.concat(rows)

club_tot = snap.groupby(["club_id", "season"]).agg(club_value_total=("snap_value", "sum"),
                                                   club_n_valued=("snap_value", "size")).reset_index()
own = snap[["player_id", "club_id", "season", "snap_value"]].rename(columns={"snap_value": "own_snap_value"})

df = df.merge(club_tot, on=["club_id", "season"], how="left")
df = df.merge(own, on=["player_id", "club_id", "season"], how="left")
df["own_snap_value"] = df.own_snap_value.fillna(0)
df["club_value_excl"] = (df.club_value_total - df.own_snap_value).clip(lower=1)
df["log_club_value_excl"] = np.log1p(df.club_value_excl)

# strength relative to the league that season (1.0 = median club of the league)
league_median = df.drop_duplicates(["club_id", "season"]).groupby(["league", "season"]).club_value_total.median()
df = df.merge(league_median.rename("league_median_value").reset_index(), on=["league", "season"], how="left")
df["club_value_rel_league"] = df.club_value_total / df.league_median_value

# ---------- 2. Club's final league position the season before ----------
lg = games[games.competition_type == "domestic_league"]
home = lg[["season", "date", "home_club_id", "home_club_position"]].set_axis(["season", "date", "club_id", "pos"], axis=1)
away = lg[["season", "date", "away_club_id", "away_club_position"]].set_axis(["season", "date", "club_id", "pos"], axis=1)
final_pos = (pd.concat([home, away]).dropna(subset=["pos"]).sort_values("date")
             .groupby(["club_id", "season"], as_index=False).last()[["club_id", "season", "pos"]])
final_pos["season"] = final_pos.season + 1                      # attach to the FOLLOWING season
final_pos = final_pos.rename(columns={"pos": "prev_season_position"})
df = df.merge(final_pos, on=["club_id", "season"], how="left")  # blank = promoted / new to top 5
df["newly_promoted"] = df.prev_season_position.isna().astype(int)

# ---------- 3. European football that season ----------
eu = games[games.competition_id.isin(["CL", "EL", "UCOL"])]
eu_rows = pd.concat([eu[["season", "competition_id", "home_club_id"]].rename(columns={"home_club_id": "club_id"}),
                     eu[["season", "competition_id", "away_club_id"]].rename(columns={"away_club_id": "club_id"})])
tier = {"CL": 3, "EL": 2, "UCOL": 1}
eu_rows["tier"] = eu_rows.competition_id.map(tier)
eu_tier = eu_rows.groupby(["club_id", "season"], as_index=False).tier.max().rename(columns={"tier": "european_tier"})
df = df.merge(eu_tier, on=["club_id", "season"], how="left")
df["european_tier"] = df.european_tier.fillna(0)                # 0 none, 1 Conf, 2 EL, 3 CL

df = df.drop(columns=["own_snap_value", "league_median_value", "club_value_total"])
df.to_csv(DATA / "features_v2.csv", index=False)

print(df.shape)
print(df[["log_club_value_excl", "club_value_rel_league", "prev_season_position",
          "newly_promoted", "european_tier"]].isna().mean().round(3))
print(df.european_tier.value_counts().sort_index())
clubs = pd.read_csv(DATA / "clubs.csv")[["club_id", "name"]].rename(columns={"name": "club_name"})
chk = df[df.season == 2025].drop_duplicates("club_id").merge(clubs, on="club_id")
cols = ["club_name", "league", "club_value_rel_league", "prev_season_position", "european_tier"]
print("\nStrongest clubs (2025/26):")
print(chk.sort_values("club_value_rel_league", ascending=False)[cols].head(8).to_string(index=False))
print("\nWeakest clubs (2025/26):")
print(chk.sort_values("club_value_rel_league")[cols].head(5).to_string(index=False))