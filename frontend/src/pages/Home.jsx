import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import GapsTable from "../components/GapsTable.jsx";
import { BallIcon, CalendarIcon, ChartIcon, GapIcon, VersusIcon } from "../components/Icons.jsx";
import PitchBackground from "../components/PitchBackground.jsx";
import PlayerCard from "../components/PlayerCard.jsx";
import SearchBox from "../components/SearchBox.jsx";
import { getFeatured, getHealth, searchPlayers } from "../api";
import { useApi } from "../hooks";

const QUICK = ["Haaland", "Yamal", "Mbappé", "Pedri", "Musiala"];

const FEATURES = [
  { to: "/compare", icon: VersusIcon, title: "Compare players", text: "Put two players side by side: value, profile and career output." },
  { to: "/stats", icon: ChartIcon, title: "Career stats", text: "Goals, assists, minutes and cards for every season of a career, split by competition." },
  { to: "/seasons", icon: CalendarIcon, title: "Season explorer", text: "Pick a year, then search or rank every player in the top five leagues." },
  { to: "/gaps", icon: GapIcon, title: "Model vs market", text: "See where the model and the Transfermarkt value disagree most." },
];

export default function Home() {
  const navigate = useNavigate();
  const [quickError, setQuickError] = useState(null);
  const { data: meta } = useApi((signal) => getHealth(signal), []);
  const { data: featured } = useApi((signal) => getFeatured(8, signal), []);

  async function quickOpen(name) {
    try {
      setQuickError(null);
      const results = await searchPlayers(name);
      if (results[0]) navigate(`/player/${results[0].player_id}`);
    } catch (e) {
      setQuickError(e.message);
    }
  }

  return (
    <>
      <section className="hero">
        <PitchBackground />
        <div className="hero-inner">
          <span className="eyebrow">
            <BallIcon width={16} height={16} /> Top 5 leagues · {meta ? meta.season_label : "2026/27 (Ongoing)"}
          </span>
          <h1>What is a footballer really worth?</h1>
          <p className="lead">
            Search any player to see his profile, every season of his career, his Transfermarkt value and
            what our model thinks he should be worth.
          </p>
          <SearchBox
            variant="hero"
            autoFocus
            placeholder="Search a player, e.g. Haaland"
            onSelect={(p) => navigate(`/player/${p.player_id}`)}
          />
          <div className="quick">
            <span>Try:</span>
            {QUICK.map((name) => (
              <button key={name} type="button" className="chip-btn" onClick={() => quickOpen(name)}>
                {name}
              </button>
            ))}
          </div>
          {quickError && <p className="hero-error">{quickError}</p>}
        </div>
        {meta && (
          <div className="stats-strip">
            <div><b>{meta.n_players.toLocaleString("en-GB")}</b><span>players</span></div>
            <div><b>5</b><span>leagues</span></div>
            <div><b>{meta.seasons.length}</b><span>seasons of stats</span></div>
            <div><b>±{meta.median_pct_error}%</b><span>typical model error</span></div>
          </div>
        )}
      </section>

      <section>
        <h2 className="section-title">Explore</h2>
        <div className="features">
          {FEATURES.map(({ to, icon: Icon, title, text }) => (
            <Link key={to} to={to} className="feature">
              <span className="feature-icon"><Icon width={26} height={26} /></span>
              <h3>{title}</h3>
              <p className="muted">{text}</p>
              <span className="feature-go">Open →</span>
            </Link>
          ))}
        </div>
      </section>

      {featured && (
        <section>
          <h2 className="section-title">Most valuable players</h2>
          <div className="pcards">
            {featured.map((p) => (
              <PlayerCard key={p.player_id} player={p} />
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="section-title">Where the model and the market disagree</h2>
        <div className="grid-2">
          <div className="card">
            <h2>Model above market</h2>
            <p className="muted small">The Transfermarkt value is below the model’s 80% range.</p>
            <GapsTable direction="under" limit={6} compact />
          </div>
          <div className="card">
            <h2>Model below market</h2>
            <p className="muted small">The Transfermarkt value is above the model’s 80% range.</p>
            <GapsTable direction="over" limit={6} compact />
          </div>
        </div>
        <p className="muted small">
          A gap shows where the model and the market disagree, not who is right. The model only sees
          statistics, so it misses reputation, transfer interest, injuries and potential.{" "}
          <Link to="/gaps">See the full list</Link>
        </p>
      </section>
    </>
  );
}
