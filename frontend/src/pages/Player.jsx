import { Link, useParams } from "react-router-dom";
import PlayerPhoto from "../components/PlayerPhoto.jsx";
import FiveYearStats from "../components/FiveYearStats.jsx";
import { getHealth, getPlayer } from "../api";
import { useApi } from "../hooks";
import {
  LEAGUES, ageFrom, cap, contractLeft, formatDate, gapClass, gapText, money, niceStep, num, seasonLabel, signedPct,
} from "../format";

function RangeBar({ low, high, estimate, market }) {
  const lo = Math.min(low, market) * 0.85;
  const hi = Math.max(high, market) * 1.08;
  const pos = (v) => `${((v - lo) / (hi - lo)) * 100}%`;
  return (
    <div className="rangebar">
      <div className="rangebar-track">
        <div
          className="rangebar-range"
          style={{ left: pos(low), width: `${((high - low) / (hi - lo)) * 100}%` }}
        />
        <div className="marker marker-est" style={{ left: pos(estimate) }} title="Model estimate" />
        <div className="marker marker-mkt" style={{ left: pos(market) }} title="Transfermarkt value" />
      </div>
      <div className="legend">
        <span><i className="dot est" /> Model estimate {money(estimate)}</span>
        <span><i className="dot range" /> 80% range {money(low)} to {money(high)}</span>
        <span><i className="dot mkt" /> Transfermarkt {money(market)}</span>
      </div>
    </div>
  );
}

// Diverging bars. Lengths use a log scale so +100% and −50% look equally big.
function Drivers({ drivers }) {
  const size = (e) => Math.abs(Math.log(1 + e / 100));
  const max = Math.max(...drivers.map((d) => size(d.effect_pct)), 0.01);
  return (
    <ul className="drivers">
      {drivers.map((d) => {
        const width = `${(size(d.effect_pct) / max) * 50}%`;
        const up = d.effect_pct >= 0;
        return (
          <li key={d.label}>
            <span className="driver-label">{d.label}</span>
            <div className="driver-bar">
              <div className={`fill ${up ? "up" : "down"}`} style={up ? { left: "50%", width } : { right: "50%", width }} />
            </div>
            <span className={`driver-pct ${up ? "up" : "down"}`}>{signedPct(d.effect_pct)}</span>
          </li>
        );
      })}
    </ul>
  );
}

function HistoryChart({ history, season, estimate, low, high }) {
  const W = 640, H = 240;
  const m = { l: 58, r: 24, t: 16, b: 32 };
  const seasons = history.map((h) => h.season);
  const maxV = Math.max(...history.map((h) => h.market_value), high) * 1.1;
  const x = (s) => {
    const i = seasons.indexOf(s);
    const span = W - m.l - m.r;
    return m.l + (seasons.length === 1 ? span / 2 : (i / (seasons.length - 1)) * span);
  };
  const y = (v) => H - m.b - (v / maxV) * (H - m.t - m.b);
  const step = niceStep(maxV / 4);
  const ticks = [];
  for (let v = 0; v <= maxV; v += step) ticks.push(v);
  const line = history.map((h) => `${x(h.season)},${y(h.market_value)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Market value by season">
      {ticks.map((v) => (
        <g key={v}>
          <line x1={m.l} x2={W - m.r} y1={y(v)} y2={y(v)} className="grid" />
          <text x={m.l - 8} y={y(v) + 4} textAnchor="end" className="axis">{money(v)}</text>
        </g>
      ))}
      {history.map((h) => (
        <text key={h.season} x={x(h.season)} y={H - 10} textAnchor="middle" className="axis">
          {seasonLabel(h.season)}
        </text>
      ))}
      <polyline points={line} className="line" fill="none" />
      {history.map((h) => (
        <circle key={h.season} cx={x(h.season)} cy={y(h.market_value)} r="4" className="pt-mkt" />
      ))}
      {seasons.includes(season) && (
        <g>
          <line x1={x(season) + 10} x2={x(season) + 10} y1={y(low)} y2={y(high)} className="est-range" />
          <circle cx={x(season) + 10} cy={y(estimate)} r="5" className="pt-est" />
        </g>
      )}
    </svg>
  );
}

function Fact({ label, children }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export default function Player() {
  const { id } = useParams();
  const { data: p, error, loading } = useApi((signal) => getPlayer(id, signal), [id]);
  const { data: meta } = useApi((signal) => getHealth(signal), []);

  if (error) {
    return (
      <>
        <p className="error">{error}</p>
        <Link to="/">Back to search</Link>
      </>
    );
  }
  if (loading || !p) return <p className="muted">Loading…</p>;

  const currentClub = p.current_club ?? p.club;
  const movedClub = currentClub !== p.club;
  const contract = contractLeft(p.contract_expiration);
  const age = ageFrom(p.date_of_birth) ?? Math.round(p.age);
  const born = [p.city_of_birth, p.country_of_birth].filter(Boolean).join(", ");

  return (
    <>
      <section className="profile">
        <PlayerPhoto src={p.image_url} name={p.name} width={170} />
        <div className="profile-main">
          <div className="chips">
            <span className="chip">{p.sub_position ?? p.position}</span>
            <span className="chip chip-light">{LEAGUES[p.league] ?? p.league}</span>
          </div>
          <h1>{p.name}</h1>
          <p className="profile-club">
            {currentClub}
            {movedClub && <span className="muted"> · {seasonLabel(p.season)} season at {p.club}</span>}
          </p>
          <dl className="facts">
            <Fact label="Age">{age} <span className="muted">({formatDate(p.date_of_birth)})</span></Fact>
            <Fact label="Nationality">{p.nationality ?? "–"}</Fact>
            <Fact label="Born">{born || "–"}</Fact>
            <Fact label="Height">{p.height_cm ? `${p.height_cm} cm` : "–"}</Fact>
            <Fact label="Preferred foot">{p.foot ? cap(p.foot) : "–"}</Fact>
            <Fact label="Contract until">
              {p.contract_expiration ? formatDate(p.contract_expiration) : "Not available"}{" "}
              {contract && <span className={`pill ${contract.tone}`}>{contract.text}</span>}
            </Fact>
            <Fact label="International">
              {p.international_caps !== null && p.international_caps !== undefined
                ? `${p.international_caps} caps, ${p.international_goals ?? 0} goals`
                : "–"}
            </Fact>
            <Fact label="Peak value">{p.highest_market_value ? money(p.highest_market_value) : "–"}</Fact>
          </dl>
          {p.profile_url && (
            <a className="ext" href={p.profile_url} target="_blank" rel="noreferrer">
              Transfermarkt profile ↗
            </a>
          )}
        </div>
      </section>

      <section className="card">
        <div className="headline">
          <div>
            <div className="label">
              Transfermarkt value{meta?.data_through ? ` (${formatDate(meta.data_through.valuations)})` : ""}
            </div>
            <div className="big">{money(p.market_value)}</div>
          </div>
          <div>
            <div className="label">Model estimate</div>
            <div className="big est">{money(p.predicted_value)}</div>
          </div>
          <div>
            <div className="label">Model vs market</div>
            <div className={`badge big-badge ${gapClass(p.gap_pct)}`}>{signedPct(p.gap_pct)}</div>
          </div>
        </div>
        <p className="muted">The model’s estimate is {gapText(p.gap_pct)}.</p>
        {p.move && (
          <div className="note-box">
            <b>Moved to {p.move.to_club}</b> ({formatDate(p.move.date)}
            {p.move.fee ? `, fee ${money(p.move.fee)}` : ""}).{" "}
            {p.move.applied
              ? `The estimate accounts for the move: ${money(p.move.estimate_before)} before, ${money(p.predicted_value)} now${
                  p.move.fee_blend ? ", blended 50/50 with the transfer fee" : ""
                }.`
              : "The estimate is unchanged: the market rarely adds value for moves to smaller squads or to clubs outside the top five leagues."}
          </div>
        )}
        <RangeBar low={p.range_low} high={p.range_high} estimate={p.predicted_value} market={p.market_value} />
        <p className="muted small">
          The 80% range is where the market value landed about 8 times in 10 for players in the model’s
          test season.
        </p>
      </section>

      <section className="grid-2">
        <div className="card">
          <h2>Why this value</h2>
          <Drivers drivers={p.drivers} />
          <p className="muted small">
            Effect of each group of factors compared with an average player
            {meta ? ` (about ${money(meta.baseline_value)})` : ""}. Effects multiply rather than add up.
          </p>
        </div>
        <div className="card">
          <h2>Market value over time</h2>
          <HistoryChart
            history={p.history}
            season={p.season}
            estimate={p.predicted_value}
            low={p.range_low}
            high={p.range_high}
          />
          <p className="muted small">
            Filled dots: Transfermarkt values at the end of each season. Hollow dot: the model’s estimate for{" "}
            {seasonLabel(p.season)}, with its range.
          </p>
        </div>
      </section>

      <section className="card">
        <h2>Career statistics, season by season</h2>
        <FiveYearStats playerId={p.player_id} />
        <p className="muted small">
          The model sees goals, assists, minutes, age, club strength and league, but not passing, defending
          or goalkeeping statistics, so it is less reliable for defenders and goalkeepers.
          {p.stats.ga_p90 !== null && ` This season: ${num(p.stats.ga_p90)} goals + assists per 90.`}
        </p>
      </section>

      <p>
        <Link to={`/compare?a=${p.player_id}`}>Compare with another player →</Link>
      </p>
    </>
  );
}
