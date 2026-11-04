import { Link, useNavigate, useParams } from "react-router-dom";
import Avatar from "../components/Avatar.jsx";
import FiveYearStats from "../components/FiveYearStats.jsx";
import PlayerCard from "../components/PlayerCard.jsx";
import SearchBox from "../components/SearchBox.jsx";
import { getFeatured, getPlayer } from "../api";
import { useApi } from "../hooks";
import { LEAGUES } from "../format";

export default function StatsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: p, error } = useApi((signal) => (id ? getPlayer(id, signal) : Promise.resolve(null)), [id]);
  const { data: featured } = useApi((signal) => getFeatured(8, signal), []);

  return (
    <>
      <h1>Player statistics: last 5 years</h1>
      <p className="muted">Search a player to see every season, split by competition.</p>
      <div className="narrow">
        <SearchBox
          variant="hero"
          placeholder="Search a player…"
          onSelect={(player) => navigate(`/stats/${player.player_id}`)}
        />
      </div>

      {error && <p className="error">{error}</p>}

      {p && (
        <>
          <div className="mini-head">
            <Avatar src={p.image_url} name={p.name} size={64} />
            <div>
              <h2>{p.name}</h2>
              <p className="muted">
                {p.current_club ?? p.club} · {LEAGUES[p.league] ?? p.league} · {p.sub_position ?? p.position}
              </p>
            </div>
            <Link to={`/player/${p.player_id}`} className="mini-link">Full profile →</Link>
          </div>
          <div className="card">
            <FiveYearStats playerId={p.player_id} />
          </div>
        </>
      )}

      {!id && featured && (
        <>
          <h2 className="section-title">Or pick a popular player</h2>
          <div className="pcards">
            {featured.map((f) => (
              <PlayerCard key={f.player_id} player={f} to={`/stats/${f.player_id}`} />
            ))}
          </div>
        </>
      )}
    </>
  );
}
