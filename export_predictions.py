"""Trains the final model, predicts the latest season, explains each prediction and
writes api/predictions.json for the website API.
Run from the project root:  python export_predictions.py
"""
import json, datetime
import numpy as np, pandas as pd
from club_context import TOP5, as_if_joined, build_club_context, flag_returns
from pathlib import Path
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import OneHotEncoder
import xgboost as xgb
from xgboost import XGBRegressor

DATA, API = Path("data"), Path("api")
API.mkdir(exist_ok=True)
FEE_WEIGHT = 0.5            # backtest_moves.py: for freshly bought players, a 50/50 blend with the fee cuts the median error from 28% to 20%
TEST_SEASON = 2025          # latest season = honest out-of-sample predictions

AS_OF = pd.Timestamp.today().normalize()      # the "now" used for summer-move estimates

df = pd.read_csv(DATA / "features_v4.csv")
clubs_all = pd.read_csv(DATA / "clubs.csv")
clubs = clubs_all[["club_id", "name"]].rename(columns={"name": "club_name"})
df = df.merge(clubs, on="club_id", how="left")
df["log_value"] = np.log1p(df.market_value)

# ---------- Features (keep in sync with train_model.py) ----------
num_cols = ["age", "minutes", "apps", "full_games", "goals", "assists", "yellows", "reds",
            "goals_p90", "assists_p90", "ga_p90", "big_ga_p90", "big_minutes", "cl_minutes",
            "form_ga_p90", "form_vs_season", "minutes_share", "team_ga_share",
            "avg_own_position", "height_in_cm",
            "log_club_value_excl", "club_value_rel_league", "prev_season_position",
            "newly_promoted", "european_tier",
            "hist_goals_p90_3y", "hist_ga_p90_3y", "hist_minutes_3y", "hist_big_ga_p90_3y",
            "hist_cl_minutes_3y", "min_prev1", "min_prev2", "ga_p90_prev1",
            "minutes_trend", "n_prior_seasons_450",
            "months_since_move", "recent_move", "club_jump", "moved_up", "last_fee_log"]
cat_cols = ["position", "sub_position", "league", "foot"]
df[cat_cols] = df[cat_cols].fillna("missing")
X, y = df[num_cols + cat_cols], df.log_value

pre = ColumnTransformer([("num", "passthrough", num_cols),
                         ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)])
Xt = pre.fit_transform(X)            # only learns category names, nothing about the target
feature_names = num_cols + list(pre.named_transformers_["cat"].get_feature_names_out(cat_cols))

def new_model(n_trees, early_stop=None):
    return XGBRegressor(n_estimators=n_trees, learning_rate=0.03, max_depth=4, subsample=0.8,
                        colsample_bytree=0.8, min_child_weight=5, reg_lambda=2.0,
                        early_stopping_rounds=early_stop, random_state=42)

# ---------- Step 1: find the right number of trees (train <= 2023, check on 2024) ----------
tr, va = (df.season <= TEST_SEASON - 2).values, (df.season == TEST_SEASON - 1).values
te = (df.season == TEST_SEASON).values
m_a = new_model(2000, early_stop=50)
m_a.fit(Xt[tr], y[tr], eval_set=[(Xt[va], y[va])], verbose=False)
best_n = int(m_a.best_iteration) + 1
resid = y[va].values - m_a.predict(Xt[va])
q_lo, q_hi = np.quantile(resid, [0.10, 0.90])        # 80% prediction range, in log space
mv = df[va].recent_move.values == 1                   # recent movers are harder to value -> wider range
q_lo_m, q_hi_m = np.quantile(resid[mv], [0.10, 0.90])

# ---------- Step 2: refit on everything before the test season ----------
final = new_model(best_n)
final.fit(Xt[tr | va], y[tr | va], verbose=False)

# ---------- Step 2b: players who changed club since the season ended ----------
# Backtest (backtest_moves.py): re-scoring a summer mover with his NEW club cut the median error from 34.8% to 31.7%
# when the new club is in the top 5 leagues and not a much poorer squad. Otherwise the market barely reacts.
tr_all = pd.read_csv(DATA / "transfers.csv", parse_dates=["transfer_date"]).dropna(subset=["to_club_id"])
tr_all["to_club_id"] = tr_all.to_club_id.astype(int)
tr_all["from_club_id"] = tr_all.from_club_id.fillna(-1).astype(int)
LIVE_MOVES = DATA / "live" / "live_moves.csv"          # optional: transfers after the dataset snapshot (update_live.py)
if LIVE_MOVES.exists():
    live = pd.read_csv(LIVE_MOVES, parse_dates=["transfer_date"])
    live["from_club_id"] = live.from_club_id.fillna(-1).astype(int)
    tr_all = pd.concat([tr_all, live], ignore_index=True)
    print(f"Added {len(live)} live transfers from {LIVE_MOVES}")
tr_all = tr_all.drop_duplicates(["player_id", "to_club_id", "transfer_date"])
tr_all["is_return"] = flag_returns(tr_all)
tr_all = tr_all[tr_all.transfer_date <= AS_OF].sort_values("transfer_date")
latest_move = tr_all.groupby("player_id").tail(1).set_index("player_id")     # most recent transfer up to today
vals = pd.read_csv(DATA / "player_valuations.csv", parse_dates=["date"])
games = pd.read_csv(DATA / "games.csv", parse_dates=["date"], usecols=["season", "date", "competition_id", "competition_type",
        "home_club_id", "away_club_id", "home_club_position", "away_club_position"])
ctx = build_club_context(TEST_SEASON, vals, games, clubs_all)
club_name = clubs.set_index("club_id").club_name.to_dict()
for _k, _v in tr_all.drop_duplicates("to_club_id").set_index("to_club_id").to_club_name.to_dict().items():
    club_name.setdefault(_k, _v)           # clubs missing from clubs.csv (e.g. just promoted) get the transfer file's name

test_df = df[te].reset_index(drop=True)
rows = test_df[num_cols + cat_cols].copy()
moves = {}
current_clubs = {}
for i, r in test_df.iterrows():
    pid = int(r.player_id)
    current_clubs[i] = r.club_name
    if pid not in latest_move.index:
        continue
    t = latest_move.loc[pid]
    if t.transfer_date > pd.Timestamp(r.valuation_date) and int(t.to_club_id) in club_name:
        current_clubs[i] = club_name[int(t.to_club_id)]          # where he plays now (loan returns included)
    # a real move: after the season's valuation date, into a different club, and not the end of a loan
    if t.to_club_id == int(r.club_id) or t.transfer_date <= pd.Timestamp(r.valuation_date) or t.is_return:
        continue
    fee = float(t.transfer_fee) if pd.notna(t.transfer_fee) else 0.0
    months = max((AS_OF - t.transfer_date).days / 30.4, 0.0)
    new = as_if_joined(r, int(t.to_club_id), int(r.club_id), ctx, months, fee, r.age)
    if new is None:
        continue
    jump = new["club_jump"]
    applied = bool(new["league"] in TOP5 and (not jump == jump or jump > -0.5))
    moves[i] = {"to_club": club_name.get(int(t.to_club_id)), "date": str(t.transfer_date.date()),
                "fee": int(fee) if fee > 0 else None, "applied": applied,
                "fee_blend": FEE_WEIGHT if applied and fee > 0 else None}
    if applied:
        for c in num_cols + cat_cols:
            rows.at[i, c] = new[c]
print(f"Players who changed club: {len(moves)} | estimate re-scored with the new club for {sum(m['applied'] for m in moves.values())}")

Xte = pre.transform(rows)
model_log = final.predict(Xte)
fee_adj = np.zeros(len(test_df))                       # pull towards the transfer fee, in log units
for i, m in moves.items():
    if m["fee_blend"]:
        fee_adj[i] = FEE_WEIGHT * (np.log(m["fee"]) - model_log[i])
pred_log = np.full(len(df), np.nan)
pred_log[te] = model_log + fee_adj
base_pred = final.predict(Xt[te])                       # what the model said before any move adjustment
is_applied = np.array([moves.get(i, {}).get("applied", False) for i in range(len(test_df))])

mae = mean_absolute_error(y[te], pred_log[te])
pct = np.abs(np.expm1(pred_log[te]) - df.market_value[te]) / df.market_value[te]
lo = np.where(is_applied, q_lo_m, q_lo); hi = np.where(is_applied, q_hi_m, q_hi)
inside = ((y[te] >= pred_log[te] + lo) & (y[te] <= pred_log[te] + hi)).mean()
print(f"Trees: {best_n} | test {TEST_SEASON}: MAE(log)={mae:.3f}, median % error={np.median(pct)*100:.1f}%")
print(f"80% range covers {inside*100:.0f}% of actual test-season values (target ~80%)")

# ---------- Step 3: explanations (exact tree contributions, in log-value units) ----------
contrib = final.get_booster().predict(xgb.DMatrix(Xte), pred_contribs=True)   # last column = baseline
bias = contrib[:, -1]
check = np.abs(contrib.sum(axis=1) + fee_adj - pred_log[te]).max()
print(f"Explanation check (contributions add up to prediction): max difference = {check:.5f}")
contrib = contrib[:, :-1]

GROUPS = {
    "Age": ["age"],
    "Playing time this season": ["minutes", "apps", "full_games", "minutes_share"],
    "Goals & assists this season": ["goals", "assists", "goals_p90", "assists_p90", "ga_p90", "team_ga_share"],
    "Output vs top teams": ["big_ga_p90", "big_minutes"],
    "Current form": ["form_ga_p90", "form_vs_season"],
    "Discipline": ["yellows", "reds"],
    "Club strength": ["log_club_value_excl", "club_value_rel_league", "avg_own_position",
                      "prev_season_position", "newly_promoted"],
    "European football": ["european_tier", "cl_minutes", "hist_cl_minutes_3y"],
    "3-season track record": ["hist_goals_p90_3y", "hist_ga_p90_3y", "hist_big_ga_p90_3y", "ga_p90_prev1"],
    "Recent club move": ["months_since_move", "recent_move", "club_jump", "moved_up", "last_fee_log"],
    "Playing time history": ["hist_minutes_3y", "min_prev1", "min_prev2", "minutes_trend", "n_prior_seasons_450"],
    "Position": [f for f in feature_names if f.startswith(("position_", "sub_position_"))],
    "League": [f for f in feature_names if f.startswith("league_")],
    "Physical": ["height_in_cm"] + [f for f in feature_names if f.startswith("foot_")],
}
idx = {f: i for i, f in enumerate(feature_names)}
assert sorted(sum(GROUPS.values(), [])) == sorted(feature_names), "every feature must be in exactly one group"
grouped = {g: contrib[:, [idx[f] for f in fs]].sum(axis=1) for g, fs in GROUPS.items()}
grouped["Recent transfer fee"] = fee_adj

# ---------- Step 4: write the JSON ----------
def clean(v):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    return round(float(v), 3) if isinstance(v, (float, np.floating)) else v

hist = (df.sort_values("season").groupby("player_id")
          .apply(lambda g: [{"season": int(s), "market_value": int(v)} for s, v in zip(g.season, g.market_value)],
                 include_groups=False).to_dict())

stat_cols = ["minutes", "apps", "goals", "assists", "ga_p90", "big_ga_p90", "form_ga_p90",
             "hist_ga_p90_3y", "min_prev1", "european_tier"]
test_rows = test_df
players = []
for i, r in test_rows.iterrows():
    pred = float(np.expm1(pred_log[te][i]))
    q1, q2 = (q_lo_m, q_hi_m) if is_applied[i] else (q_lo, q_hi)
    drivers = sorted(({"label": g, "effect_pct": round((float(np.exp(grouped[g][i])) - 1) * 100, 1)}
                      for g in grouped), key=lambda d: -abs(d["effect_pct"]))[:6]
    players.append({
        "player_id": int(r.player_id), "name": r["name"], "season": int(r.season),
        "club": r.club_name, "current_club": current_clubs[i], "league": r.league, "position": r.position, "sub_position": r.sub_position,
        "age": round(float(r.age), 1), "nationality": r.country_of_citizenship,
        "market_value": int(r.market_value),
        "predicted_value": int(round(pred, -5)),
        "range_low": int(round(pred * np.exp(q1), -5)), "range_high": int(round(pred * np.exp(q2), -5)),
        "gap_pct": round((pred / r.market_value - 1) * 100, 1),
        "stats": {c: clean(r[c]) for c in stat_cols},
        "drivers": drivers,
        "history": hist.get(int(r.player_id), []),
        "move": ({**moves[i], "estimate_before": int(round(float(np.expm1(base_pred[i])), -5)),
                  "effect_pct": round((pred / float(np.expm1(base_pred[i])) - 1) * 100, 1)} if i in moves else None),
    })

meta = {"season": TEST_SEASON, "season_label": f"{TEST_SEASON}/{str(TEST_SEASON + 1)[2:]}",
        "n_players": len(players), "median_pct_error": round(float(np.median(pct) * 100), 1),
        "range_level": 0.8, "baseline_value": int(round(float(np.expm1(bias.mean())), -5)),
        "generated": datetime.date.today().isoformat(), "as_of": str(AS_OF.date()),
        "note": "Estimates from a statistical model, not official valuations."}
with open(API / "predictions.json", "w", encoding="utf-8") as f:
    json.dump({"meta": meta, "players": players}, f, ensure_ascii=False)
final.save_model(API / "model.json")
print(f"Wrote api/predictions.json ({len(players)} players, "
      f"{(API / 'predictions.json').stat().st_size / 1e6:.1f} MB) and api/model.json")

show = sorted(players, key=lambda p: -p["gap_pct"])
print("\nExample, first player:", json.dumps({k: players[0][k] for k in
      ["name", "club", "age", "market_value", "predicted_value", "range_low", "range_high"]}, ensure_ascii=False))
print("Drivers:", players[0]["drivers"][:4])