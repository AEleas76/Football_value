"""Does re-scoring a summer mover with his NEW club get closer to his December Transfermarkt value?
For each season S: train on seasons before S, take players who changed club in Jul-Oct of S+1,
predict them (a) as before the move and (b) as if already at the new club, compare with the December value.
Run from the project root:  python backtest_moves.py
"""
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor
from club_context import build_club_context, as_if_joined, flag_returns

DATA = Path("data")
df = pd.read_csv(DATA / "features_v4.csv", parse_dates=["valuation_date"])
vals = pd.read_csv(DATA / "player_valuations.csv", parse_dates=["date"])
games = pd.read_csv(DATA / "games.csv", parse_dates=["date"], usecols=["season", "date", "competition_id", "competition_type",
        "home_club_id", "away_club_id", "home_club_position", "away_club_position"])
clubs = pd.read_csv(DATA / "clubs.csv")[["club_id", "domestic_competition_id"]]
tr = pd.read_csv(DATA / "transfers.csv", parse_dates=["transfer_date"]).dropna(subset=["from_club_id", "to_club_id"])
tr["from_club_id"] = tr.from_club_id.astype(int); tr["to_club_id"] = tr.to_club_id.astype(int)
tr["is_return"] = flag_returns(tr)

num = ["age", "minutes", "apps", "full_games", "goals", "assists", "yellows", "reds", "goals_p90", "assists_p90", "ga_p90",
       "big_ga_p90", "big_minutes", "cl_minutes", "form_ga_p90", "form_vs_season", "minutes_share", "team_ga_share",
       "avg_own_position", "height_in_cm", "log_club_value_excl", "club_value_rel_league", "prev_season_position",
       "newly_promoted", "european_tier", "hist_goals_p90_3y", "hist_ga_p90_3y", "hist_minutes_3y", "hist_big_ga_p90_3y",
       "hist_cl_minutes_3y", "min_prev1", "min_prev2", "ga_p90_prev1", "minutes_trend", "n_prior_seasons_450",
       "months_since_move", "recent_move", "club_jump", "moved_up", "last_fee_log"]
cat = ["position", "sub_position", "league", "foot"]
df[cat] = df[cat].fillna("missing")
pre = ColumnTransformer([("n", "passthrough", num), ("c", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat)])
pre.fit(df[num + cat])
df["y"] = np.log1p(df.market_value)

def to_matrix(rows):
    x = pd.DataFrame(rows).reset_index(drop=True)
    x[num] = x[num].apply(pd.to_numeric, errors="coerce").astype(float)
    x[cat] = x[cat].astype(str)
    return pre.transform(x[num + cat])

allres = []
for S in [2022, 2023, 2024]:
    train = df[df.season < S]
    model = XGBRegressor(n_estimators=600, learning_rate=0.03, max_depth=4, subsample=0.8, colsample_bytree=0.8,
                         min_child_weight=5, reg_lambda=2.0, random_state=42)
    model.fit(pre.transform(train[num + cat]), train.y, verbose=False)
    ctx = build_club_context(S, vals, games, clubs)
    rows = df[df.season == S].set_index("player_id")

    window = tr[(tr.transfer_date >= f"{S+1}-07-01") & (tr.transfer_date <= f"{S+1}-10-31") & tr.player_id.isin(rows.index)]
    window = window.sort_values("transfer_date").groupby("player_id").last()
    window = window[window.to_club_id != rows.loc[window.index, "club_id"]]
    n_ret = int(window.is_return.sum()); n_all = len(window)
    window = window[~window.is_return]               # loan returns get no push from the market
    print(f"season {S}: {n_all} movers in the window, {n_ret} are loan returns and are excluded")
    dec = vals[(vals.date >= f"{S+1}-11-15") & (vals.date <= f"{S+1}-12-31")].sort_values("date").groupby("player_id").last()
    dec = dec.market_value_in_eur

    keep = []
    for pid, t in window.iterrows():
        if pid not in dec.index: continue
        row = rows.loc[pid]
        when = pd.Timestamp(f"{S+1}-12-15")
        months = (when - t.transfer_date).days / 30.4
        age_now = row.age + (when - row.valuation_date).days / 365.25
        base = row.copy(); base["age"] = age_now
        new = as_if_joined(row, int(t.to_club_id), int(row.club_id), ctx, months, t.transfer_fee, age_now)
        if new is None: continue
        keep.append((pid, row, t, base, new))
    if not keep: continue
    pb = np.expm1(model.predict(to_matrix([k[3] for k in keep])))
    pn = np.expm1(model.predict(to_matrix([k[4] for k in keep])))
    for (pid, row, t, base, new), b, n in zip(keep, pb, pn):
        allres.append(dict(season=S, name=row["name"], old_club=row.club_id, new=int(t.to_club_id), fee=t.transfer_fee,
                           jump=new.club_jump, dest_top5=bool(new['league'] in ['GB1','ES1','L1','IT1','FR1']), actual=dec[pid], before=b, after=n))
r = pd.DataFrame(allres)
r["err_before"] = abs(r.before - r.actual) / r.actual
r["err_after"] = abs(r.after - r.actual) / r.actual
r["bias_before"] = np.log(r.before / r.actual); r["bias_after"] = np.log(r.after / r.actual)
def show(label, d):
    print(f"{label:<34} n={len(d):4d}  median error  {d.err_before.median()*100:5.1f}% -> {d.err_after.median()*100:5.1f}%   "
          f"median bias {np.expm1(d.bias_before.median())*100:+6.1f}% -> {np.expm1(d.bias_after.median())*100:+6.1f}%")
show("all summer movers", r)
show("moved to a richer squad (jump>=0.5)", r[r["jump"] >= 0.5])
show("moved to a similar squad", r[(r["jump"] > -0.5) & (r["jump"] < 0.5)])
show("moved to a poorer squad", r[r["jump"] <= -0.5])
show("movers with a fee", r[r.fee > 0])
for S in [2022, 2023, 2024]:
    show(f"  season {S} movers", r[r.season == S])

# ---------- which rule should the website use? ----------
def policy_error(final):
    return (abs(final - r.actual) / r.actual).median() * 100
rules = {
    "never adjust (old behaviour)": r.before,
    "always use the new club": r.after,
    "use new club only if it is not a poorer squad": np.where(r["jump"].fillna(0) > -0.5, r.after, r.before),
    "never go below the old estimate: max(old, new)": np.maximum(r.before, r.after),
    "only upward moves: new club if squad richer, else old": np.where(r["jump"].fillna(0) >= 0.5, r.after, r.before),
}
print("\nmedian error over all movers by rule:")
for name, final in rules.items():
    print(f"  {name:<56} {policy_error(final):5.1f}%   | richer squads only: {(abs(pd.Series(final, index=r.index)[r['jump']>=0.5] - r.actual[r['jump']>=0.5]) / r.actual[r['jump']>=0.5]).median()*100:5.1f}%")

r["dest_top5"] = r.dest_top5.astype(bool)
print()
for lab, mk in [("fee > 0 (bought)", r.fee > 0), ("fee = 0 or unknown (free / loan)", ~(r.fee > 0))]:
    d = r[mk]
    print(f"{lab:<34} n={len(d):4d}  before {d.err_before.median()*100:5.1f}%  always-new {d.err_after.median()*100:5.1f}%  | richer squads: n={int((d['jump']>=0.5).sum()):3d} before {d[d['jump']>=0.5].err_before.median()*100:5.1f}% -> {d[d['jump']>=0.5].err_after.median()*100:5.1f}%")
ok = r["jump"].fillna(0) > -0.5
print("\nby destination:")
for label, mask in [("destination in top-5 leagues", r.dest_top5), ("destination outside top 5", ~r.dest_top5)]:
    d = r[mask]
    print(f"  {label:<30} n={len(d):4d}  before {d.err_before.median()*100:5.1f}%  always-new {d.err_after.median()*100:5.1f}%  "
          f"rule(not poorer) {(abs(np.where((d['jump'].fillna(0) > -0.5), d.after, d.before) - d.actual) / d.actual).median()*100:5.1f}%")
final = np.where(ok & r.dest_top5, r.after, r.before)
print(f"\nrule 'not poorer AND destination in top 5': {policy_error(final):.1f}%  (vs {policy_error(r.before):.1f}% before)")

# ---------- should a fresh transfer fee pull the estimate towards the fee? ----------
paid = r[(r.fee > 0) & (r["jump"].fillna(0) > -0.5) & r.dest_top5].copy()
print(f"\nbought players moving to a not-poorer top-5 club (n={len(paid)}): median error by blend weight on the fee")
for w in [0.0, 0.25, 0.4, 0.5, 0.6, 0.75, 1.0]:
    blend = np.exp((1 - w) * np.log(paid.after) + w * np.log(paid.fee))
    print(f"  weight on fee {w:4.2f}: {(abs(blend - paid.actual) / paid.actual).median() * 100:5.1f}%   bias {np.expm1(np.median(np.log(blend / paid.actual)))*100:+6.1f}%")
big = paid[paid.fee >= 30e6]
print(f"fees >= 30m (n={len(big)}):", {w: round((abs(np.exp((1-w)*np.log(big.after)+w*np.log(big.fee)) - big.actual)/big.actual).median()*100, 1) for w in [0, 0.5, 1.0]})