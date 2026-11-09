import { useState } from "react";
import { getPlayerStats } from "../api";
import { useApi } from "../hooks";
import { money, niceStep, num, seasonLabel, seasonShort } from "../format";

function SeasonBars({ seasons, selected, onPick, compact }) {
  const W = 640, H = 230;
  const m = { l: 34, r: 12, t: 26, b: 30 };
  const maxV = Math.max(...seasons.flatMap((s) => [s.goals, s.assists]), 5);
  const step = niceStep(maxV / 4);
  const top = Math.ceil(maxV / step) * step;
  const ticks = [];
  for (let v = 0; v <= top; v += step) ticks.push(v);
  const gw = (W - m.l - m.r) / seasons.length;
  const bw = Math.min(26, gw / 3);
  const y = (v) => H - m.b - (v / top) * (H - m.t - m.b);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Goals and assists per season">
      {ticks.map((v) => (
        <g key={v}>
          <line x1={m.l} x2={W - m.r} y1={y(v)} y2={y(v)} className="grid" />
          <text x={m.l - 6} y={y(v) + 4} textAnchor="end" className="axis">{v}</text>
        </g>
      ))}
      <g className="legend-svg">
        <rect x={W - 150} y="4" width="10" height="10" rx="2" className="bar goals" />
        <text x={W - 135} y="13" className="axis">Goals</text>
        <rect x={W - 85} y="4" width="10" height="10" rx="2" className="bar assists" />
        <text x={W - 70} y="13" className="axis">Assists</text>
      </g>
      {seasons.map((s, i) => {
        const cx = m.l + gw * i + gw / 2;
        return (
          <g key={s.season} className={`bars ${s.season === selected ? "active" : ""}`} onClick={() => onPick(s.season)}>
            <rect className="bar-hit" x={m.l + gw * i} y={m.t} width={gw} height={H - m.t - m.b} />
            <rect className="bar goals" x={cx - bw - 2} y={y(s.goals)} width={bw} height={H - m.b - y(s.goals)} rx="3" />
            <text className="bar-val" x={cx - bw / 2 - 2} y={y(s.goals) - 5} textAnchor="middle">{s.goals}</text>
            <rect className="bar assists" x={cx + 2} y={y(s.assists)} width={bw} height={H - m.b - y(s.assists)} rx="3" />
            <text className="bar-val" x={cx + bw / 2 + 2} y={y(s.assists) - 5} textAnchor="middle">{s.assists}</text>
            <text className="axis" x={cx} y={H - 9} textAnchor="middle">{compact ? seasonShort(s.season) : seasonLabel(s.season)}{s.partial ? "*" : ""}</text>
          </g>
        );
      })}
    </svg>
  );
}

export default function FiveYearStats({ playerId }) {
  const { data, error, loading } = useApi((signal) => getPlayerStats(playerId, signal), [playerId]);
  const [picked, setPicked] = useState(null);

  if (error) return <p className="error">{error}</p>;
  if (loading || !data) return <p className="muted">Loading statistics…</p>;
  const seasons = data.seasons;
  if (seasons.length === 0) return <p className="muted">No match data found for this player.</p>;

  const selected = seasons.find((s) => s.season === picked) ?? seasons[seasons.length - 1];
  const total = (key) => seasons.reduce((sum, s) => sum + s[key], 0);

  return (
    <div>
      <p className="muted small">
        All competitions, including cups, European games and international matches.{" "}
        <b>Click a season</b> to see it split by competition.
        {seasons.some((s) => s.partial) && " * The current season is still in progress."}
      </p>

      <SeasonBars seasons={seasons} selected={selected.season} onPick={setPicked} compact={seasons.length > 8} />

      <div className="table-wrap">
        <table className="table stats-table">
          <thead>
            <tr>
              <th>Season</th>
              <th>Club</th>
              <th className="num">Apps</th>
              <th className="num">Minutes</th>
              <th className="num">Goals</th>
              <th className="num">Assists</th>
              <th className="num">G+A / 90</th>
              <th className="num">Cards</th>
              <th className="num">Value</th>
            </tr>
          </thead>
          <tbody>
            {[...seasons].reverse().map((s) => (
              <tr
                key={s.season}
                className={s.season === selected.season ? "row-active" : "row-click"}
                onClick={() => setPicked(s.season)}
              >
                <td><b>{seasonLabel(s.season)}</b>{s.partial && <span className="muted small"> so far</span>}</td>
                <td>{s.club ?? "–"}</td>
                <td className="num">{s.apps}</td>
                <td className="num">{s.minutes.toLocaleString("en-GB")}</td>
                <td className="num">{s.goals}</td>
                <td className="num">{s.assists}</td>
                <td className="num">{num(s.ga_p90)}</td>
                <td className="num">
                  <span className="card-y" title="Yellow cards">{s.yellows}</span>{" "}
                  <span className="card-r" title="Red cards">{s.reds}</span>
                </td>
                <td className="num">{s.market_value ? money(s.market_value) : "–"}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={2}><b>Career total ({seasons.length} seasons)</b></td>
              <td className="num">{total("apps")}</td>
              <td className="num">{total("minutes").toLocaleString("en-GB")}</td>
              <td className="num">{total("goals")}</td>
              <td className="num">{total("assists")}</td>
              <td className="num" />
              <td className="num">
                <span className="card-y">{total("yellows")}</span> <span className="card-r">{total("reds")}</span>
              </td>
              <td className="num" />
            </tr>
          </tfoot>
        </table>
      </div>

      <h3 className="subhead">
        {seasonLabel(selected.season)}{selected.partial ? " (so far)" : ""} by competition{selected.club ? ` · ${selected.club}` : ""}
      </h3>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Competition</th>
              <th className="num">Apps</th>
              <th className="num">Minutes</th>
              <th className="num">Goals</th>
              <th className="num">Assists</th>
              <th className="num">Cards</th>
            </tr>
          </thead>
          <tbody>
            {selected.competitions.map((c) => (
              <tr key={c.name}>
                <td>
                  <span className={`kind kind-${c.kind.toLowerCase()}`}>{c.kind}</span> {c.name}
                </td>
                <td className="num">{c.apps}</td>
                <td className="num">{c.minutes.toLocaleString("en-GB")}</td>
                <td className="num">{c.goals}</td>
                <td className="num">{c.assists}</td>
                <td className="num">
                  <span className="card-y">{c.yellows}</span> <span className="card-r">{c.reds}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
