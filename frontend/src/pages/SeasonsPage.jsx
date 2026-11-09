import { useState } from "react";
import { Link } from "react-router-dom";
import { getHealth, getLeaders } from "../api";
import { useApi, useDebounced } from "../hooks";
import { LEAGUES, POSITIONS, money, num, seasonLabel } from "../format";

const COLUMNS = [
  ["goals", "Goals"],
  ["assists", "Assists"],
  ["ga", "G+A"],
  ["ga_p90", "G+A / 90"],
  ["minutes", "Minutes"],
  ["market_value", "Value"],
];

export default function SeasonsPage() {
  const [pickedSeason, setSeason] = useState(null);
  const [position, setPosition] = useState("");
  const [league, setLeague] = useState("");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("ga");
  const [pickedMinutes, setMinMinutes] = useState(null);
  const debouncedQ = useDebounced(q, 300);

  const { data: meta } = useApi((signal) => getHealth(signal), []);
  const seasons = meta ? [...meta.seasons].reverse() : [2026, 2025];
  const partial = meta?.partial_seasons ?? [];
  const season = pickedSeason ?? seasons[0];                       // newest season by default
  const minMinutes = pickedMinutes ?? (partial.includes(season) ? 180 : 900);

  const { data, error, loading } = useApi(
    (signal) =>
      getLeaders(season, { position, league, q: debouncedQ, sort, min_minutes: minMinutes, limit: 50 }, signal),
    [season, position, league, debouncedQ, sort, minMinutes]
  );

  return (
    <>
      <h1>Season explorer</h1>
      <p className="muted">
        Pick a season and search or rank every player who played at least 450 minutes in the top five
        leagues. All competitions are counted.
        {partial.includes(season) && ` ${seasonLabel(season)} is still in progress, so the numbers are partial.`}
      </p>

      <div className="filters">
        <label>
          Season
          <select value={season} onChange={(e) => setSeason(Number(e.target.value))}>
            {seasons.map((s) => (
              <option key={s} value={s}>{seasonLabel(s)}{partial.includes(s) ? " (so far)" : ""}</option>
            ))}
          </select>
        </label>
        <label>
          Player name
          <input type="search" value={q} placeholder="e.g. Salah" onChange={(e) => setQ(e.target.value)} />
        </label>
        <label>
          Position
          <select value={position} onChange={(e) => setPosition(e.target.value)}>
            <option value="">All</option>
            {POSITIONS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
        <label>
          League
          <select value={league} onChange={(e) => setLeague(e.target.value)}>
            <option value="">All</option>
            {Object.entries(LEAGUES).map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
        </label>
        <label>
          Minimum minutes
          <select value={minMinutes} onChange={(e) => setMinMinutes(Number(e.target.value))}>
            <option value={90}>90</option>
            <option value={180}>180</option>
            <option value={450}>450</option>
            <option value={900}>900</option>
            <option value={1800}>1800</option>
            <option value={2700}>2700</option>
          </select>
        </label>
      </div>

      <div className="card">
        {error && <p className="error">{error}</p>}
        {loading && !data && <p className="muted">Loading…</p>}
        {data && data.rows.length === 0 && <p className="muted">No players match these filters.</p>}
        {data && data.rows.length > 0 && (
          <>
            <p className="muted small">
              {seasonLabel(season)} · showing the top {data.rows.length} of {data.total} players. Click a
              column heading to rank by it.
            </p>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Player</th>
                    <th>Club</th>
                    <th>Pos</th>
                    <th className="num">Age</th>
                    <th className="num">Apps</th>
                    {COLUMNS.map(([key, label]) => (
                      <th key={key} className="num" aria-sort={sort === key ? "descending" : "none"}>
                        <button type="button" className={`th-btn ${sort === key ? "on" : ""}`} onClick={() => setSort(key)}>
                          {label}{sort === key ? " ↓" : ""}
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((r, i) => (
                    <tr key={r.player_id}>
                      <td className="muted">{i + 1}</td>
                      <td>
                        {r.has_profile ? <Link to={`/player/${r.player_id}`}>{r.name}</Link> : r.name}
                      </td>
                      <td>
                        {r.club}
                        <div className="muted small">{LEAGUES[r.league] ?? r.league}</div>
                      </td>
                      <td>{r.position}</td>
                      <td className="num">{Math.round(r.age)}</td>
                      <td className="num">{r.apps}</td>
                      <td className="num">{r.goals}</td>
                      <td className="num">{r.assists}</td>
                      <td className="num">{r.ga}</td>
                      <td className="num">{num(r.ga_p90)}</td>
                      <td className="num">{r.minutes.toLocaleString("en-GB")}</td>
                      <td className="num">{money(r.market_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}
