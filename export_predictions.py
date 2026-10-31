"""Trains the final model, predicts the latest season, explains each prediction and
writes api/predictions.json for the website API.
Run from the project root:  python export_predictions.py
"""
import json, datetime
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import OneHotEncoder
import xgboost as xgb
from xgboost import XGBRegressor

DATA, API = Path("data"), Path("api")
API.mkdir(exist_ok=True)
TEST_SEASON = 2025          # latest season = honest out-of-sample predictions

df = pd.read_csv(DATA / "features_v3.csv")
clubs = pd.read_csv(DATA / "clubs.csv")[["club_id", "name"]].rename(columns={"name": "club_name"})
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
            "minutes_trend", "n_prior_seasons_450"]
cat_cols = ["position", "sub_position", "league", "foot"]
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

# ---------- Step 2: refit on everything before the test season, predict the test season ----------
final = new_model(best_n)
final.fit(Xt[tr | va], y[tr | va], verbose=False)
pred_log = final.predict(Xt)

mae = mean_absolute_error(y[te], pred_log[te])
pct = np.abs(np.expm1(pred_log[te]) - df.market_value[te]) / df.market_value[te]
inside = ((y[te] >= pred_log[te] + q_lo) & (y[te] <= pred_log[te] + q_hi)).mean()
print(f"Trees: {best_n} | test {TEST_SEASON}: MAE(log)={mae:.3f}, median % error={np.median(pct)*100:.1f}%")
print(f"80% range covers {inside*100:.0f}% of actual test-season values (target ~80%)")

# ---------- Step 3: explanations (exact tree contributions, in log-value units) ----------
contrib = final.get_booster().predict(xgb.DMatrix(Xt[te]), pred_contribs=True)   # last column = baseline
bias = contrib[:, -1]
check = np.abs(contrib.sum(axis=1) - pred_log[te]).max()
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
    "Playing time history": ["hist_minutes_3y", "min_prev1", "min_prev2", "minutes_trend", "n_prior_seasons_450"],
    "Position": [f for f in feature_names if f.startswith(("position_", "sub_position_"))],
    "League": [f for f in feature_names if f.startswith("league_")],
    "Physical": ["height_in_cm"] + [f for f in feature_names if f.startswith("foot_")],
}
idx = {f: i for i, f in enumerate(feature_names)}
assert sorted(sum(GROUPS.values(), [])) == sorted(feature_names), "every feature must be in exactly one group"
grouped = {g: contrib[:, [idx[f] for f in fs]].sum(axis=1) for g, fs in GROUPS.items()}

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
test_rows = df[te].reset_index(drop=True)
players = []
for i, r in test_rows.iterrows():
    pred = float(np.expm1(pred_log[te][i]))
    drivers = sorted(({"label": g, "effect_pct": round((float(np.exp(grouped[g][i])) - 1) * 100, 1)}
                      for g in GROUPS), key=lambda d: -abs(d["effect_pct"]))[:6]
    players.append({
        "player_id": int(r.player_id), "name": r["name"], "season": int(r.season),
        "club": r.club_name, "league": r.league, "position": r.position, "sub_position": r.sub_position,
        "age": round(float(r.age), 1), "nationality": r.country_of_citizenship,
        "market_value": int(r.market_value),
        "predicted_value": int(round(pred, -5)),
        "range_low": int(round(pred * np.exp(q_lo), -5)), "range_high": int(round(pred * np.exp(q_hi), -5)),
        "gap_pct": round((pred / r.market_value - 1) * 100, 1),
        "stats": {c: clean(r[c]) for c in stat_cols},
        "drivers": drivers,
        "history": hist.get(int(r.player_id), []),
    })

meta = {"season": TEST_SEASON, "season_label": f"{TEST_SEASON}/{str(TEST_SEASON + 1)[2:]}",
        "n_players": len(players), "median_pct_error": round(float(np.median(pct) * 100), 1),
        "range_level": 0.8, "baseline_value": int(round(float(np.expm1(bias.mean())), -5)),
        "generated": datetime.date.today().isoformat(),
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