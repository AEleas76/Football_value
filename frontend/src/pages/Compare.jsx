import { Link, useSearchParams } from "react-router-dom";
import SearchBox from "../components/SearchBox.jsx";
import { comparePlayers } from "../api";
import { useApi } from "../hooks";
import { LEAGUES, gapText, money, num, signedPct } from "../format";

const ROWS = [
  ["Club", (p) => p.club],
  ["League", (p) => LEAGUES[p.league] ?? p.league],
  ["Position", (p) => p.sub_position ?? p.position],
  ["Age", (p) => Math.round(p.age)],
  ["Transfermarkt value", (p) => money(p.market_value)],
  ["Model estimate", (p) => money(p.predicted_value)],
  ["80% range", (p) => `${money(p.range_low)} to ${money(p.range_high)}`],
  ["Model vs market", (p) => `${signedPct(p.gap_pct)} (${gapText(p.gap_pct)})`],
  ["Minutes", (p) => p.stats.minutes],
  ["Goals", (p) => p.stats.goals],
  ["Assists", (p) => p.stats.assists],
  ["Goals + assists per 90", (p) => num(p.stats.ga_p90)],
  ["Per 90 vs top-6 teams", (p) => num(p.stats.big_ga_p90)],
  ["Per 90, last 3 seasons", (p) => num(p.stats.hist_ga_p90_3y)],
  ["Biggest factors", (p) => p.drivers.slice(0, 3).map((d) => `${d.label} ${signedPct(d.effect_pct)}`).join(", ")],
];

export default function Compare() {
  const [params, setParams] = useSearchParams();
  const a = params.get("a");
  const b = params.get("b");

  const { data, error, loading } = useApi(
    (signal) => (a && b ? comparePlayers(a, b, signal) : Promise.resolve(null)),
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
      <div className="grid-2">
        <div>
          <div className="label">First player</div>
          <SearchBox placeholder="Search first player…" onSelect={(p) => pick("a", p)} />
          {data && <p className="muted small">Now showing: <Link to={`/player/${data.a.player_id}`}>{data.a.name}</Link></p>}
        </div>
        <div>
          <div className="label">Second player</div>
          <SearchBox placeholder="Search second player…" onSelect={(p) => pick("b", p)} />
          {data && <p className="muted small">Now showing: <Link to={`/player/${data.b.player_id}`}>{data.b.name}</Link></p>}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && a && b && !data && <p className="muted">Loading…</p>}
      {!(a && b) && <p className="muted">Pick two players to compare them side by side.</p>}

      {data && (
        <div className="card table-wrap">
          <table className="table compare">
            <thead>
              <tr>
                <th />
                <th>{data.a.name}</th>
                <th>{data.b.name}</th>
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
      )}
    </>
  );
}
