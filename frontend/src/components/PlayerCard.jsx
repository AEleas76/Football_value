import { Link } from "react-router-dom";
import PlayerPhoto from "./PlayerPhoto.jsx";
import { money } from "../format";

export default function PlayerCard({ player, to }) {
  return (
    <Link to={to ?? `/player/${player.player_id}`} className="pcard">
      <div className="pcard-photo">
        <PlayerPhoto src={player.image_url} name={player.name} width={96} />
      </div>
      <div className="pcard-name">{player.name}</div>
      <div className="muted small">
        {player.club} · {player.position}
      </div>
      <div className="pcard-values">
        <div>
          <span className="label">Market</span>
          <b>{money(player.market_value)}</b>
        </div>
        <div>
          <span className="label">Model</span>
          <b>{money(player.predicted_value)}</b>
        </div>
      </div>
    </Link>
  );
}
