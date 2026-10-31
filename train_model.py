import pandas as pd, numpy as np
from pathlib import Path
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA = Path("data")
df = pd.read_csv(DATA / "features_v1.csv")

# ---------- Target ----------
df["log_value"] = np.log1p(df["market_value"])

# ---------- Features ----------
num_cols = ["age", "minutes", "apps", "full_games", "goals", "assists", "yellows", "reds",
            "goals_p90", "assists_p90", "ga_p90", "big_ga_p90", "big_minutes", "cl_minutes",
            "form_ga_p90", "form_vs_season", "minutes_share", "team_ga_share",
            "avg_own_position", "height_in_cm"]
cat_cols = ["position", "sub_position", "league", "foot"]
X = df[num_cols + cat_cols]
y = df["log_value"]

# ---------- Time-based split (never random!) ----------
train = df.season <= 2023
valid = df.season == 2024
test  = df.season == 2025
print("rows  train/valid/test:", train.sum(), valid.sum(), test.sum())

def report(name, y_true_log, y_pred_log):
    mae_log = mean_absolute_error(y_true_log, y_pred_log)
    pct_err = np.abs(np.expm1(y_pred_log) - np.expm1(y_true_log)) / np.expm1(y_true_log)
    print(f"{name:<22} MAE(log)={mae_log:.3f}  median % error={np.median(pct_err)*100:5.1f}%  "
          f"R2(log)={r2_score(y_true_log, y_pred_log):.3f}")

# ---------- Model 1: baseline (ridge regression) ----------
pre = ColumnTransformer([
    ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num_cols),
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
])
ridge = Pipeline([("pre", pre), ("model", Ridge(alpha=3.0))])
ridge.fit(X[train], y[train])
report("Ridge   valid (2024)", y[valid], ridge.predict(X[valid]))
report("Ridge   test  (2025)", y[test],  ridge.predict(X[test]))

# ---------- Model 2: gradient boosting ----------
pre_gb = ColumnTransformer([
    ("num", "passthrough", num_cols),     # boosting handles missing values itself
    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
])
Xt_train = pre_gb.fit_transform(X[train])
Xt_valid = pre_gb.transform(X[valid])
Xt_test  = pre_gb.transform(X[test])
feature_names = num_cols + list(pre_gb.named_transformers_["cat"].get_feature_names_out(cat_cols))

try:
    from xgboost import XGBRegressor
    gb = XGBRegressor(n_estimators=2000, learning_rate=0.03, max_depth=4, subsample=0.8,
                      colsample_bytree=0.8, min_child_weight=5, reg_lambda=2.0,
                      early_stopping_rounds=50, random_state=42)
    gb.fit(Xt_train, y[train], eval_set=[(Xt_valid, y[valid])], verbose=False)
    print("XGBoost stopped at", gb.best_iteration, "trees")
except ImportError:
    from sklearn.ensemble import HistGradientBoostingRegressor
    gb = HistGradientBoostingRegressor(max_depth=4, learning_rate=0.05, max_iter=400, random_state=42)
    gb.fit(Xt_train, y[train])
    print("(xgboost not installed here, used scikit-learn boosting instead)")

report("Boost   valid (2024)", y[valid], gb.predict(Xt_valid))
report("Boost   test  (2025)", y[test],  gb.predict(Xt_test))

# ---------- Error by position group (test season) ----------
tmp = df[test].copy()
tmp["pred_log"] = gb.predict(Xt_test)
tmp["abs_pct_err"] = np.abs(np.expm1(tmp.pred_log) - tmp.market_value) / tmp.market_value
print("\nMedian % error by position (test season):")
print((tmp.groupby("position").abs_pct_err.median() * 100).round(1))

# ---------- Which features matter? (permutation importance on the test season) ----------
from sklearn.inspection import permutation_importance
imp = permutation_importance(gb, Xt_test, y[test], n_repeats=5, random_state=0,
                             scoring="neg_mean_absolute_error")
imp_s = pd.Series(imp.importances_mean, index=feature_names).sort_values(ascending=False)
print("\nTop 12 features (increase in error when shuffled):")
print(imp_s.head(12).round(4))

# ---------- Biggest misses (interesting for the website later) ----------
tmp["pred_value"] = np.expm1(tmp.pred_log).round(-4)
tmp["gap"] = tmp.pred_value - tmp.market_value
cols = ["name", "age", "position", "minutes", "goals", "assists", "market_value", "pred_value"]
print("\nMost UNDERvalued by the model (pred >> market):")
print(tmp.sort_values("gap", ascending=False)[cols].head(8).to_string(index=False))
print("\nMost OVERvalued by the model (pred << market):")
print(tmp.sort_values("gap")[cols].head(8).to_string(index=False))