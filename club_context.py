"""Helpers that describe a club as the model sees it, and re-score a player as if he had joined that club.
Used by export_predictions.py (summer-move estimates) and backtest_moves.py (checks the idea).
"""
import numpy as np, pandas as pd

TOP5 = ["GB1", "ES1", "L1", "IT1", "FR1"]

def build_club_context(season, vals, games, clubs):
    """One row per club: squad value on 30 Jun after `season`, league, average / final league position, European tier."""
    cutoff = pd.Timestamp(year=season + 1, month=6, day=30)
    snap = vals[(vals.date <= cutoff) & (vals.date >= cutoff - pd.Timedelta(days=365))]
    snap = snap.sort_values("date").groupby("player_id", as_index=False).last()
    total = snap.groupby("current_club_id").market_value_in_eur.sum().rename("total")

    g = games[games.season == season]
    lg = g[g.competition_id.isin(TOP5)]
    pos = pd.concat([
        lg[["date", "home_club_id", "home_club_position", "competition_id"]].set_axis(["date", "club_id", "pos", "league"], axis=1),
        lg[["date", "away_club_id", "away_club_position", "competition_id"]].set_axis(["date", "club_id", "pos", "league"], axis=1)])
    pos = pos.dropna(subset=["pos"]).sort_values("date")
    league = pos.groupby("club_id").league.agg(lambda s: s.value_counts().index[0])
    avg_pos = pos.groupby("club_id").pos.mean().rename("avg_pos")
    final_pos = pos.groupby("club_id").pos.last().rename("final_pos")

    eu = g[g.competition_id.isin(["CL", "EL", "UCOL"])]
    eu = pd.concat([eu[["competition_id", "home_club_id"]].set_axis(["c", "club_id"], axis=1),
                    eu[["competition_id", "away_club_id"]].set_axis(["c", "club_id"], axis=1)])
    euro_tier = eu.assign(t=eu.c.map({"CL": 3, "EL": 2, "UCOL": 1})).groupby("club_id").t.max().rename("euro_tier")

    ctx = pd.concat([total, league.rename("league"), avg_pos, final_pos, euro_tier], axis=1)
    ctx.index.name = "club_id"
    ctx["euro_tier"] = ctx.euro_tier.fillna(0)
    # clubs outside the top 5 last season (e.g. just promoted): take today's league from clubs.csv
    fallback = clubs.set_index("club_id").domestic_competition_id
    ctx["league"] = ctx.league.fillna(ctx.index.to_series().map(fallback))
    return ctx

def as_if_joined(row, new_club_id, old_club_id, ctx, months_since_move, fee, age_now):
    """Copy of a feature row with the club-related features of `new_club_id` and the move features filled in."""
    r = row.copy()
    if new_club_id not in ctx.index or ctx.loc[new_club_id, "total"] != ctx.loc[new_club_id, "total"]:
        return None                                              # club unknown to our data: leave the prediction alone
    c = ctx.loc[new_club_id]
    old_total = ctx.loc[old_club_id, "total"] if old_club_id in ctx.index else np.nan
    league = c.league if isinstance(c.league, str) else r["league"]
    same_league = ctx[ctx.league == league].total
    r["league"] = league
    r["log_club_value_excl"] = np.log1p(c.total)
    r["club_value_rel_league"] = c.total / same_league.median() if len(same_league) else np.nan
    r["prev_season_position"] = c.final_pos
    r["newly_promoted"] = int(pd.isna(c.final_pos))
    r["avg_own_position"] = c.avg_pos
    r["european_tier"] = c.euro_tier
    jump = np.log1p(c.total) - np.log1p(old_total) if old_total == old_total else np.nan
    r["months_since_move"] = months_since_move
    r["recent_move"] = 1
    r["club_jump"] = jump
    r["moved_up"] = int(jump == jump and jump >= 0.5)
    r["last_fee_log"] = np.log1p(fee) if fee and fee > 0 else 0.0
    r["age"] = age_now
    return r

def flag_returns(tr):
    """True for transfers where the player goes back to a club he had left earlier (typically the end of a loan).
    The market does not give a value push for these. Needs columns player_id, from_club_id, to_club_id, transfer_date."""
    tr = tr.reset_index(drop=True)
    later = tr[["player_id", "from_club_id", "to_club_id", "transfer_date"]].copy()
    later["_i"] = np.arange(len(tr))
    earlier = tr[["player_id", "from_club_id", "to_club_id", "transfer_date"]].rename(
        columns={"from_club_id": "e_from", "to_club_id": "e_to", "transfer_date": "e_date"})
    # earlier transfer: C -> F ; this transfer: F -> C
    m = later.merge(earlier, left_on=["player_id", "to_club_id", "from_club_id"],
                    right_on=["player_id", "e_from", "e_to"], how="inner")
    m = m[m.e_date < m.transfer_date]
    flags = np.zeros(len(tr), dtype=bool)
    flags[m["_i"].unique()] = True
    return flags