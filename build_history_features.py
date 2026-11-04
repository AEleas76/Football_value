"""Adds multi-season history features to features_v2.csv and writes features_v3.csv.
Uses only performance data (no previous market values).
Run from the project root:  python build_history_features.py
"""
import pandas as pd, numpy as np
from pathlib import Path

DATA = Path("data")
df    = pd.read_csv(DATA / "features_v2.csv")
games = pd.read_csv(DATA / "games.csv")
apps  = pd.read_csv(DATA / "appearances.csv",
                    usecols=["game_id", "player_id", "player_club_id", "competition_id",
                             "goals", "assists", "minutes_played"])

# ---------- 1. Player-season table from ALL matches (any club, any league, lookback to 2017) ----------
g = games[["game_id", "season", "competition_id", "competition_type", "home_club_id", "away_club_id",
           "home_club_position", "away_club_position", "date"]].copy()
is_wc_2026 = (g.competition_id == "FIWC") & (pd.to_datetime(g.date).dt.year == 2026)
g.loc[is_wc_2026, "season"] = 2025
g = g.drop(columns=["competition_id", "date"])

a = apps.merge(g, on="game_id", how="inner")
a = a[a.season >= 2017]
is_home = a.player_club_id == a.home_club_id
a["opp_position"] = np.where(is_home, a.away_club_position, a.home_club_position)
a["is_big_opp"] = (a.competition_type == "domestic_league") & (a.opp_position <= 6)
a["is_cl"] = a.competition_id == "CL"
a["ga"] = a.goals + a.assists
a["big_min"] = np.where(a.is_big_opp, a.minutes_played, 0)
a["big_ga"]  = np.where(a.is_big_opp, a.ga, 0)
a["cl_min"]  = np.where(a.is_cl, a.minutes_played, 0)

P = a.groupby(["player_id", "season"], as_index=False).agg(
    minutes=("minutes_played", "sum"), goals=("goals", "sum"), ga=("ga", "sum"),
    big_min=("big_min", "sum"), big_ga=("big_ga", "sum"), cl_min=("cl_min", "sum"))

# ---------- 2. Attach the previous two seasons to every row ----------
base = df[["player_id", "season"]].drop_duplicates()
H = base.copy()
for k in (0, 1, 2):
    Pk = P.copy()
    Pk["season"] = Pk.season + k                      # season s-k stats now sit on season s
    Pk = Pk.rename(columns={c: f"{c}_{k}" for c in ["minutes", "goals", "ga", "big_min", "big_ga", "cl_min"]})
    H = H.merge(Pk, on=["player_id", "season"], how="left")
H = H.fillna(0)

# ---------- 3. Features ----------
W = {0: 0.5, 1: 0.3, 2: 0.2}                           # recent seasons count more

def weighted_p90(num):                                  # minutes-weighted, recency-weighted per-90 rate
    n = sum(W[k] * H[f"{num}_{k}"] for k in W)
    m = sum(W[k] * H[f"minutes_{k}"] for k in W)
    return np.where(m > 0, n / m * 90, np.nan)

H["hist_goals_p90_3y"] = weighted_p90("goals")
H["hist_ga_p90_3y"]    = weighted_p90("ga")
H["hist_minutes_3y"]   = sum(W[k] * H[f"minutes_{k}"] for k in W)

big_min_raw = H.big_min_0 + H.big_min_1 + H.big_min_2
big_ga_w = sum(W[k] * H[f"big_ga_{k}"] for k in W)
big_min_w = sum(W[k] * H[f"big_min_{k}"] for k in W)
H["hist_big_ga_p90_3y"] = np.where(big_min_raw >= 270, big_ga_w / big_min_w.replace(0, np.nan) * 90, np.nan)

H["hist_cl_minutes_3y"] = H.cl_min_0 + H.cl_min_1 + H.cl_min_2
H["min_prev1"] = H.minutes_1
H["min_prev2"] = H.minutes_2
H["ga_p90_prev1"] = np.where(H.minutes_1 >= 450, H.ga_1 / H.minutes_1.replace(0, np.nan) * 90, np.nan)
H["minutes_trend"] = H.minutes_0 - H.minutes_1
H["n_prior_seasons_450"] = (H.minutes_1 >= 450).astype(int) + (H.minutes_2 >= 450).astype(int)

keep = ["player_id", "season", "hist_goals_p90_3y", "hist_ga_p90_3y", "hist_minutes_3y",
        "hist_big_ga_p90_3y", "hist_cl_minutes_3y", "min_prev1", "min_prev2",
        "ga_p90_prev1", "minutes_trend", "n_prior_seasons_450"]
out = df.merge(H[keep], on=["player_id", "season"], how="left")
out.to_csv(DATA / "features_v3.csv", index=False)

print(out.shape)
print(out[keep[2:]].isna().mean().round(3))
print(out.n_prior_seasons_450.value_counts().sort_index())
print(out[out.name.isin(["Jamal Musiala", "Erling Haaland"])][
    ["name", "season", "minutes", "ga_p90", "hist_ga_p90_3y", "min_prev1", "minutes_trend", "market_value"]].to_string(index=False))