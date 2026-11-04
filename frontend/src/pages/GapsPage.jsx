import { useState } from "react";
import GapsTable from "../components/GapsTable.jsx";
import { LEAGUES, POSITIONS } from "../format";

export default function GapsPage() {
  const [direction, setDirection] = useState("under");
  const [position, setPosition] = useState("");
  const [league, setLeague] = useState("");
  const [minMinutes, setMinMinutes] = useState(900);

  return (
    <>
      <h1>Model vs market</h1>
      <p className="muted">
        The clearest disagreements between the model and the Transfermarkt value: players whose market
        value falls outside the model’s 80% range, ranked by the size of the gap in euros. Players
        below €10m are left out, because small values produce huge percentage gaps.
      </p>

      <div className="filters">
        <label>
          Show
          <select value={direction} onChange={(e) => setDirection(e.target.value)}>
            <option value="under">Model above market</option>
            <option value="over">Model below market</option>
          </select>
        </label>
        <label>
          Position
          <select value={position} onChange={(e) => setPosition(e.target.value)}>
            <option value="">All</option>
            {POSITIONS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label>
          League
          <select value={league} onChange={(e) => setLeague(e.target.value)}>
            <option value="">All</option>
            {Object.entries(LEAGUES).map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Minimum minutes
          <select value={minMinutes} onChange={(e) => setMinMinutes(Number(e.target.value))}>
            <option value={450}>450</option>
            <option value={900}>900</option>
            <option value={1800}>1800</option>
            <option value={2700}>2700</option>
          </select>
        </label>
      </div>

      <div className="card">
        <GapsTable
          direction={direction}
          position={position}
          league={league}
          minMinutes={minMinutes}
          limit={30}
        />
      </div>
    </>
  );
}
