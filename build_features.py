import pandas as pd, numpy as np
from pathlib import Path

DATA = Path("data")
TOP5 = ["GB1", "ES1", "L1", "IT1", "FR1"]
FIRST_SEASON = 2020   # 2020 = the 2020/21 season

# ---------- 1. Load ----------
players = pd.read_csv(DATA/"players.csv", parse_dates=["date_of_birth"])
vals    = pd.read_csv(DATA/"player_valuations.csv", parse_dates=["date"])
games   = pd.read_csv(DATA/"games.csv", parse_dates=["date"])
cgames  = pd.read_csv(DATA/"club_games.csv")
apps    = pd.read_csv(DATA/"appearances.csv", parse_dates=["date"],
                      usecols=["game_id","player_id","player_club_id","date","competition_id",
                               "yellow_cards","red_cards","goals","assists","minutes_played"])

# ---------- 2. Target: one valuation per player per season ----------
# Season S runs 1 Jul S -> 30 Jun S+1. Target = last valuation in Jan-Jun of S+1.
# Exception: The 2026 World Cup concluded on 19 July 2026, so July 2026 post-tournament valuations
# count as the season 2025 end-of-season valuation. For ongoing season (>= 2026), take the latest available valuation.
v = vals[vals.player_club_domestic_competition_id.isin(TOP5)].copy()
is_post_wc_2026_val = (v.date.dt.year == 2026) & (v.date.dt.month == 7)
v["season"] = np.where(is_post_wc_2026_val, 2025, np.where(v.date.dt.month >= 7, v.date.dt.year, v.date.dt.year - 1))
v = v[v.season >= FIRST_SEASON]
v_completed = v[(v.season < 2026) & (((v.date.dt.month <= 6) & (v.date.dt.month >= 1)) | ((v.date.dt.year == 2026) & (v.date.dt.month == 7)))]
v_ongoing = v[v.season >= 2026]
v = pd.concat([v_completed, v_ongoing]).sort_values("date").groupby(["player_id","season"], as_index=False).last()
v = v.rename(columns={"market_value_in_eur":"market_value",
                      "current_club_id":"club_id",
                      "player_club_domestic_competition_id":"league",
                      "date":"valuation_date"})[
    ["player_id","season","valuation_date","market_value","club_id","league"]]
v = v[v.market_value > 0]

# ---------- 3. Match-level table ----------
g = games[["game_id","season","competition_id","competition_type",
           "home_club_id","away_club_id","home_club_position","away_club_position","date"]].copy()
# Count the entire 2026 FIFA World Cup as part of the 2025–26 season (season 2025)
is_wc_2026 = (g.competition_id == "FIWC") & (pd.to_datetime(g.date).dt.year == 2026)
g.loc[is_wc_2026, "season"] = 2025
g = g.drop(columns=["date"])

a = apps.merge(g, on="game_id", how="inner", suffixes=("","_g"))
a = a[a.season >= FIRST_SEASON]
is_home = a.player_club_id == a.home_club_id
a["opp_position"] = np.where(is_home, a.away_club_position, a.home_club_position)
a["own_position"] = np.where(is_home, a.home_club_position, a.away_club_position)
a["is_league"]  = a.competition_type.eq("domestic_league")
a["is_big_opp"] = a.is_league & (a.opp_position <= 6)
a["is_cl"]      = a.competition_id.eq("CL")
a["ga"]         = a.goals + a.assists
a = a.sort_values(["player_id","date"])

# ---------- 4. Season aggregates per player (and club) ----------
def per90(x, mins): return np.where(mins > 0, x / mins * 90, np.nan)

key = ["player_id","season"]
agg = a.groupby(key).agg(
    apps=("game_id","count"), minutes=("minutes_played","sum"),
    goals=("goals","sum"), assists=("assists","sum"),
    yellows=("yellow_cards","sum"), reds=("red_cards","sum"),
    full_games=("minutes_played", lambda s: (s >= 60).sum()),
    avg_own_position=("own_position","mean"),
).reset_index()
agg["goals_p90"]   = per90(agg.goals, agg.minutes)
agg["assists_p90"] = per90(agg.assists, agg.minutes)
agg["ga_p90"]      = per90(agg.goals + agg.assists, agg.minutes)

big = a[a.is_big_opp].groupby(key).agg(big_minutes=("minutes_played","sum"),
                                       big_ga=("ga","sum")).reset_index()
cl  = a[a.is_cl].groupby(key).agg(cl_minutes=("minutes_played","sum")).reset_index()
agg = agg.merge(big, on=key, how="left").merge(cl, on=key, how="left")
agg[["big_minutes","big_ga","cl_minutes"]] = agg[["big_minutes","big_ga","cl_minutes"]].fillna(0)
agg["big_ga_p90"] = per90(agg.big_ga, agg.big_minutes)
agg.loc[agg.big_minutes < 180, "big_ga_p90"] = np.nan   # too little data -> missing

# Current form: goals+assists per 90 over the last 10 appearances of the season
last10 = a.groupby(key).tail(10).groupby(key).agg(l10_ga=("ga","sum"), l10_min=("minutes_played","sum")).reset_index()
last10["form_ga_p90"] = per90(last10.l10_ga, last10.l10_min)
agg = agg.merge(last10[key + ["form_ga_p90"]], on=key, how="left")
agg["form_vs_season"] = agg.form_ga_p90 - agg.ga_p90

# ---------- 5. Team context: games played & goals scored by the player's club ----------
cg = cgames.merge(games[["game_id","season","competition_type"]], on="game_id")
cg = cg[cg.season >= FIRST_SEASON]
team = cg.groupby(["club_id","season"]).agg(team_games=("game_id","count"),
                                            team_goals=("own_goals","sum")).reset_index()

# ---------- 6. Assemble ----------
df = v.merge(agg, on=key, how="inner")
df = df.merge(team, on=["club_id","season"], how="left")
df["minutes_share"]   = df.minutes / (df.team_games * 90)
df["team_ga_share"]   = (df.goals + df.assists) / df.team_goals.replace(0, np.nan)
df = df.merge(players[["player_id","name","date_of_birth","position","sub_position",
                       "country_of_citizenship","height_in_cm","foot"]], on="player_id", how="left")
df["age"] = (df.valuation_date - df.date_of_birth).dt.days / 365.25
df = df.drop(columns=["date_of_birth"])

# Filter: need playing time (450+ mins for completed seasons, 180+ mins for ongoing season)
min_mins = np.where(df.season >= 2026, 180, 450)
df = df[df.minutes >= min_mins].reset_index(drop=True)

df.to_csv(DATA/"features_v1.csv", index=False)
print(df.shape)
print(df.groupby("season").size())
print(df.isna().mean().round(3).sort_values(ascending=False).head(8))
print(df[["name","season","age","position","minutes","goals","assists","big_ga_p90","form_ga_p90","market_value"]].sample(8, random_state=1))