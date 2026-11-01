import { Link, useNavigate } from "react-router-dom";
import GapsTable from "../components/GapsTable.jsx";
import SearchBox from "../components/SearchBox.jsx";
import { getHealth } from "../api";
import { useApi } from "../hooks";

export default function Home() {
  const navigate = useNavigate();
  const { data: meta } = useApi((signal) => getHealth(signal), []);

  return (
    <>
      <section className="hero">
        <h1>What is a footballer worth?</h1>
        <p className="lead">
          A statistical model trained on past market values and match data for the top five European
          leagues. Search a player to see the model’s estimate and the factors behind it.
        </p>
        <SearchBox
          autoFocus
          placeholder="Try “Haaland”, “Yamal”, “Gyökeres”…"
          onSelect={(p) => navigate(`/player/${p.player_id}`)}
        />
        {meta && (
          <p className="muted small">
            {meta.n_players} players · season {meta.season_label} · typical error about {meta.median_pct_error}%
          </p>
        )}
      </section>

      <section className="grid-2">
        <div className="card">
          <h2>Model above market</h2>
          <p className="muted small">Players the model values well above their Transfermarkt value.</p>
          <GapsTable direction="under" limit={8} compact />
        </div>
        <div className="card">
          <h2>Model below market</h2>
          <p className="muted small">Players the market values well above the model’s estimate.</p>
          <GapsTable direction="over" limit={8} compact />
        </div>
      </section>

      <p className="muted small note">
        A gap shows where the model and the market disagree, not who is right. The model only sees
        statistics, so it misses reputation, transfer interest, injuries and potential.{" "}
        <Link to="/gaps">See the full list</Link>
      </p>
    </>
  );
}
