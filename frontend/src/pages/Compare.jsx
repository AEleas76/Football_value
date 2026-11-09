import { Link, useSearchParams } from "react-router-dom";
import PlayerPhoto from "../components/PlayerPhoto.jsx";
import SearchBox from "../components/SearchBox.jsx";
import { comparePlayers, getPlayerStats } from "../api";
import { useApi } from "../hooks";
import { LEAGUES, ageFrom, cap, formatDate, gapText, money, niceStep, num, seasonLabel, seasonShort, signedPct } from "../format";

const ROWS = [
  ["Club", (p) => p.current_club ?? p.club],
  ["League", (p) => LEAGUES[p.league] ?? p.league],
  ["Position", (p) => p.sub_position ?? p.position],
  ["Age", (p) => ageFrom(p.date_of_birth) ?? Math.round(p.age)],
  ["Nationality", (p) => p.nationality],
  ["Height", (p) => (p.height_cm ? `${p.height_cm} cm` : null)],
  ["Preferred foot", (p) => (p.foot ? cap(p.foot) : null)],
  ["Contract until", (p) => (p.contract_expiration ? formatDate(p.contract_expiration) : null)],
  ["International", (p) => (p.international_caps != null ? `${p.international_caps} caps, ${p.international_goals ?? 0} goals` : null)],
  ["Market value", (p) => money(p.market_value)],
  ["Model estimate", (p) => money(p.predicted_value)],
  ["80% range", (p) => `${money(p.range_low)} to ${money(p.range_high)}`],
  ["Model vs market", (p) => `${signedPct(p.gap_pct)} (${gapText(p.gap_pct)})`],
  ["Minutes this season", (p) => p.stats.minutes],
  ["Goals this season", (p) => p.stats.goals],
  ["Assists this season", (p) => p.stats.assists],
  ["Goals + assists per 90", (p) => num(p.stats.ga_p90)],
  ["Per 90 vs top-6 teams", (p) => num(p.stats.big_ga_p90)],
  ["Per 90, last 3 seasons", (p) => num(p.stats.hist_ga_p90_3y)],
  ["Biggest factors", (p) => p.drivers.slice(0, 3).map((d) => `${d.label} ${signedPct(d.effect_pct)}`).join(", ")],
];

// Goals + assists per season for two players, as grouped bars
function PairChart({ a, b, statsA, statsB }) {
  const W = 640, H = 240;
  const m = { l: 34, r: 12, t: 28, b: 30 };
  const seasons = [...new Set([...statsA.seasons, ...statsB.seasons].map((s) => s.season))].sort();
  const ga = (stats, season) => {
    const row = stats.seasons.find((s) => s.season === season);
    return row ? row.goals + row.assists : 0;
  };
  const maxV = Math.max(...seasons.flatMap((s) => [ga(statsA, s), ga(statsB, s)]), 5);
  const step = niceStep(maxV / 4);
  const top = Math.ceil(maxV / step) * step;
  const ticks = [];
  for (let v = 0; v <= top; v += step) ticks.push(v);
  const gw = (W - m.l - m.r) / seasons.length;
  const bw = Math.min(28, gw / 3);
  const y = (v) => H - m.b - (v / top) * (H - m.t - m.b);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Goals plus assists per season">
      {ticks.map((v) => (
        <g key={v}>
          <line x1={m.l} x2={W - m.r} y1={y(v)} y2={y(v)} className="grid" />
          <text x={m.l - 6} y={y(v) + 4} textAnchor="end" className="axis">{v}</text>
        </g>
      ))}
      {seasons.map((s, i) => {
        const cx = m.l + gw * i + gw / 2;
        const va = ga(statsA, s);
        const vb = ga(statsB, s);
        return (
          <g key={s}>
            <rect className="bar goals" x={cx - bw - 2} y={y(va)} width={bw} height={H - m.b - y(va)} rx="3" />
            <text className="bar-val" x={cx - bw / 2 - 2} y={y(va) - 5} textAnchor="middle">{va}</text>
            <rect className="bar assists" x={cx + 2} y={y(vb)} width={bw} height={H - m.b - y(vb)} rx="3" />
            <text className="bar-val" x={cx + bw / 2 + 2} y={y(vb) - 5} textAnchor="middle">{vb}</text>
            <text className="axis" x={cx} y={H - 9} textAnchor="middle">{seasons.length > 8 ? seasonShort(s) : seasonLabel(s)}</text>
          </g>
        );
      })}
      <g>
        <rect x={m.l} y="6" width="10" height="10" rx="2" className="bar goals" />
        <text x={m.l + 15} y="15" className="axis">{a}</text>
        <rect x={m.l + 170} y="6" width="10" height="10" rx="2" className="bar assists" />
        <text x={m.l + 185} y="15" className="axis">{b}</text>
      </g>
    </svg>
  );
}

function Header({ player }) {
  return (
    <div className="cmp-head">
      <PlayerPhoto src={player.image_url} name={player.name} width={64} />
      <div>
        <Link to={`/player/${player.player_id}`} className="cmp-name">{player.name}</Link>
        <div className="muted small">{player.current_club ?? player.club}</div>
      </div>
    </div>
  );
}

export default function Compare() {
  const [params, setParams] = useSearchParams();
  const a = params.get("a");
  const b = params.get("b");

  const { data, error, loading } = useApi(
    (signal) => (a && b ? comparePlayers(a, b, signal) : Promise.resolve(null)),
    [a, b]
  );
  const { data: stats } = useApi(
    (signal) =>
      a && b ? Promise.all([getPlayerStats(a, signal), getPlayerStats(b, signal)]) : Promise.resolve(null),
    [a, b]
  );

  function pick(slot, player) {
    const next = new URLSearchParams(params);
    next.set(slot, player.player_id);
    setParams(next);
  }

  return (
    <>
      <h1>Compare players</h1>
      <p className="muted">Pick two players to compare their profile, value and career output.</p>
      <div className="grid-2">
        <div>
          <div className="label">First player</div>
          <SearchBox placeholder="Search first player…" onSelect={(p) => pick("a", p)} />
        </div>
        <div>
          <div className="label">Second player</div>
          <SearchBox placeholder="Search second player…" onSelect={(p) => pick("b", p)} />
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && a && b && !data && <p className="muted">Loading…</p>}
      {!(a && b) && <p className="muted">Choose both players to see them side by side.</p>}

      {data && (
        <>
          <div className="card table-wrap">
            <table className="table compare">
              <thead>
                <tr>
                  <th />
                  <th><Header player={data.a} /></th>
                  <th><Header player={data.b} /></th>
                </tr>
              </thead>
              <tbody>
                {ROWS.map(([label, fn]) => (
                  <tr key={label}>
                    <th scope="row">{label}</th>
                    <td>{fn(data.a) ?? "–"}</td>
                    <td>{fn(data.b) ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {stats && (
            <div className="card">
              <h2>Goals + assists, season by season</h2>
              <PairChart a={data.a.name} b={data.b.name} statsA={stats[0]} statsB={stats[1]} />
              <p className="muted small">All competitions, including cups, European games and international matches.</p>
            </div>
          )}
        </>
      )}
    </>
  );
}
