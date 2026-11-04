import { Link } from "react-router-dom";
import { getGaps } from "../api";
import { useApi } from "../hooks";
import { LEAGUES, gapClass, money, signedPct } from "../format";
import Avatar from "./Avatar.jsx";

export default function GapsTable({ direction, position, league, minMinutes = 900, limit = 20, compact = false }) {
  const { data, error, loading } = useApi(
    (signal) => getGaps({ direction, position, league, min_minutes: minMinutes, limit }, signal),
    [direction, position, league, minMinutes, limit]
  );

  if (error) return <p className="error">{error}</p>;
  if (loading && !data) return <p className="muted">Loading…</p>;
  if (data && data.length === 0) return <p className="muted">No players match these filters.</p>;

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Player</th>
            {!compact && <th>Position</th>}
            <th className="num">Market</th>
            <th className="num">Model</th>
            <th className="num">Gap</th>
          </tr>
        </thead>
        <tbody>
          {data.map((p) => (
            <tr key={p.player_id}>
              <td>
                <div className="cell-player">
                  <Avatar src={p.image_url} name={p.name} size={compact ? 32 : 40} />
                  <div>
                    <Link to={`/player/${p.player_id}`}>{p.name}</Link>
                    <div className="muted small">
                      {p.club}
                      {!compact && ` · ${LEAGUES[p.league] ?? p.league}`}
                    </div>
                  </div>
                </div>
              </td>
              {!compact && <td>{p.position}</td>}
              <td className="num">{money(p.market_value)}</td>
              <td className="num">{money(p.predicted_value)}</td>
              <td className="num">
                <span className={`badge ${gapClass(p.gap_pct)}`}>{signedPct(p.gap_pct)}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
