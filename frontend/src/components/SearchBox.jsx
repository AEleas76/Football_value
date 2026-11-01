import { useEffect, useRef, useState } from "react";
import { searchPlayers } from "../api";
import { money } from "../format";

export default function SearchBox({ onSelect, placeholder = "Search a player…", autoFocus = false }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [error, setError] = useState(null);
  const boxRef = useRef(null);

  // search 250 ms after the user stops typing
  useEffect(() => {
    if (q.trim().length < 2) {
      setResults([]);
      setError(null);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      searchPlayers(q.trim(), controller.signal)
        .then((r) => {
          setResults(r);
          setActive(0);
          setError(null);
          setOpen(true);
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [q]);

  // close the list when clicking elsewhere
  useEffect(() => {
    const handler = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function choose(player) {
    setOpen(false);
    setQ("");
    setResults([]);
    onSelect(player);
  }

  function onKeyDown(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[active]) {
      e.preventDefault();
      choose(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const showEmpty = open && !error && q.trim().length >= 2 && results.length === 0;

  return (
    <div className="search" ref={boxRef}>
      <input
        type="search"
        value={q}
        placeholder={placeholder}
        autoFocus={autoFocus}
        aria-label="Search players"
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {open && results.length > 0 && (
        <ul className="search-list" role="listbox">
          {results.map((p, i) => (
            <li
              key={p.player_id}
              role="option"
              aria-selected={i === active}
              className={i === active ? "active" : ""}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(p);
              }}
            >
              <span className="search-name">{p.name}</span>
              <span className="muted">
                {p.club} · {p.position} · {Math.round(p.age)}
              </span>
              <span className="search-value">{money(p.market_value)}</span>
            </li>
          ))}
        </ul>
      )}
      {showEmpty && <div className="search-list search-empty">No player found (only 450+ minutes in 2025/26)</div>}
      {error && <div className="search-list search-empty error">{error}</div>}
    </div>
  );
}
