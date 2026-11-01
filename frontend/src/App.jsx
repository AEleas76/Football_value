import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import SearchBox from "./components/SearchBox.jsx";
import Compare from "./pages/Compare.jsx";
import GapsPage from "./pages/GapsPage.jsx";
import Home from "./pages/Home.jsx";
import Player from "./pages/Player.jsx";

export default function App() {
  const navigate = useNavigate();
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="brand">Football Value</Link>
          <nav>
            <NavLink to="/gaps">Model vs market</NavLink>
            <NavLink to="/compare">Compare</NavLink>
          </nav>
          <div className="topbar-search">
            <SearchBox placeholder="Search a player…" onSelect={(p) => navigate(`/player/${p.player_id}`)} />
          </div>
        </div>
      </header>

      <main className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/player/:id" element={<Player />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/gaps" element={<GapsPage />} />
          <Route path="*" element={<p>Page not found. <Link to="/">Go home</Link></p>} />
        </Routes>
      </main>

      <footer className="footer">
        Estimates come from a statistical model and are not official valuations. Market values and match
        data originate from Transfermarkt.
      </footer>
    </>
  );
}
