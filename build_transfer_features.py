"""Adds transfer / club-move features to features_v3.csv and writes features_v4.csv.
Idea: the market pays a premium when a player joins a bigger club, which season stats can't show.
Run from the project root:  python build_transfer_features.py
"""
import pandas as pd, numpy as np
from pathlib import Path
from club_context import flag_returns

DATA = Path("data")
df  = pd.read_csv(DATA / "features_v3.csv", parse_dates=["valuation_date"])
tr  = pd.read_csv(DATA / "transfers.csv", parse_dates=["transfer_date"])
vals = pd.read_csv(DATA / "player_valuations.csv", parse_dates=["date"])

# ---------- club squad value per season (same snapshot rule as build_club_features.py) ----------
rows = []
for s in sorted(df.season.unique()):
    cutoff = pd.Timestamp(year=s + 1, month=1, day=1)
    snap = vals[(vals.date <= cutoff) & (vals.date >= cutoff - pd.Timedelta(days=365))]
    snap = snap.sort_values("date").groupby("player_id", as_index=False).last()
    tot = snap.groupby("current_club_id").market_value_in_eur.sum().rename("club_total").reset_index()
    tot.columns = ["club_id", "club_total"]
    tot["season"] = s
    rows.append(tot)
club_total = pd.concat(rows)

# ---------- when did the player join his current club, and from where? ----------
tr = tr[["player_id", "transfer_date", "from_club_id", "to_club_id", "transfer_fee"]].dropna(subset=["to_club_id"]).copy()
tr["to_club_id"] = tr.to_club_id.astype(int)
tr["from_club_id"] = tr.from_club_id.fillna(-1).astype(int)
tr["is_return"] = flag_returns(tr)          # going back to a club he had left = end of a loan, not a real move
m = df[["player_id", "season", "valuation_date", "club_id"]].reset_index().merge(
    tr, left_on=["player_id", "club_id"], right_on=["player_id", "to_club_id"], how="left")
m = m[m.transfer_date.isna() | (m.transfer_date <= m.valuation_date)]          # only moves already known then
m = m.sort_values("transfer_date").groupby("index", as_index=False).last()       # most recent move into this club
m["months_since_move"] = ((m.valuation_date - m.transfer_date).dt.days / 30.4).clip(upper=60)
m["months_since_move"] = m.months_since_move.fillna(60)                          # no move found = long-time / academy player
m.loc[m.months_since_move > 60, "months_since_move"] = 60

m = m.merge(club_total.rename(columns={"club_id": "from_club_id", "club_total": "from_total"}),
            on=["from_club_id", "season"], how="left")
m = m.merge(club_total.rename(columns={"club_total": "to_total"}).rename(columns={"club_id": "club_id"}),
            on=["club_id", "season"], how="left")
m["club_jump"] = np.log1p(m.to_total) - np.log1p(m.from_total)                   # >0 = moved to a richer squad
ret = m.is_return.fillna(False).astype(bool)
m.loc[ret, "months_since_move"] = 60                                              # loan returns count as "no move"
recent = (m.months_since_move <= 12) & ~ret
m.loc[~recent, "club_jump"] = np.nan                                              # only meaningful for fresh moves
m["recent_move"] = recent.astype(int)
m["moved_up"] = (recent & (m.club_jump >= 0.5)).astype(int)
m["last_fee_log"] = np.where(recent & (m.transfer_fee > 0), np.log1p(m.transfer_fee), 0.0)

feat = ["months_since_move", "recent_move", "club_jump", "moved_up", "last_fee_log"]
out = df.reset_index().merge(m[["index"] + feat], on="index", how="left").drop(columns="index")
out[["recent_move", "moved_up"]] = out[["recent_move", "moved_up"]].fillna(0).astype(int)
out["months_since_move"] = out.months_since_move.fillna(60)
out["last_fee_log"] = out.last_fee_log.fillna(0)
assert len(out) == len(df), "row count changed"
out.to_csv(DATA / "features_v4.csv", index=False)

print(out.shape)
print("loan returns neutralised:", int(ret.sum()))
print("recent moves (<=12 months):", out.recent_move.sum(), f"({out.recent_move.mean()*100:.1f}%) | moved to a much richer squad:", out.moved_up.sum(),
      "| with a fee:", (out.last_fee_log > 0).sum())
print(out.groupby("season").agg(recent=("recent_move", "sum"), up=("moved_up", "sum")).T.to_string())
print(out[out.moved_up == 1][["name", "season", "club_jump", "last_fee_log", "market_value"]].assign(fee_m=lambda d: np.expm1(d.last_fee_log) / 1e6).head(5).round(2).to_string(index=False))