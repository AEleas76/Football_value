import { useState } from "react";
import { initials, photoCandidates } from "../format";

// Full, uncropped player portrait. Tries the large Transfermarkt image first, then the thumbnail, then initials.
export default function PlayerPhoto({ src, name, width = 150 }) {
  const candidates = photoCandidates(src);
  const [state, setState] = useState({ src, index: 0 });
  const index = state.src === src ? state.index : 0;
  if (index >= candidates.length) {
    return (
      <div className="photo photo-fallback" style={{ width }} role="img" aria-label={name}>
        {initials(name)}
      </div>
    );
  }
  return (
    <img
      className="photo"
      style={{ width }}
      src={candidates[index]}
      alt={name}
      referrerPolicy="no-referrer"
      onError={() => setState({ src, index: index + 1 })}
    />
  );
}
