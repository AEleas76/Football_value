import { useState } from "react";
import { initials } from "../format";

// Player photo with uncropped portrait display (like Transfermarkt) and fallback
export default function Avatar({ src, name, size = 48, shape = "round" }) {
  const [useBig, setUseBig] = useState(true);
  const [failedSrc, setFailedSrc] = useState(false);

  const isPortrait = shape === "portrait";
  const isSquare = shape === "square";

  // Transfermarkt header URLs (139x181) can be upgraded to high-res 'big' (300x390)
  const bigSrc = src && src.includes("/portrait/header/")
    ? src.replace("/portrait/header/", "/portrait/big/")
    : src;
  const activeSrc = useBig ? bigSrc : src;

  const style = {
    width: size,
    height: isPortrait ? Math.round(size * 1.33) : size,
    aspectRatio: isPortrait ? "3 / 4" : "1 / 1",
    fontSize: Math.max(11, size * 0.36),
  };

  const className = `avatar ${isPortrait ? "avatar-portrait" : isSquare ? "avatar-square" : ""}`;

  if (!src || failedSrc) {
    return (
      <div className={`${className} avatar-fallback`} style={style} role="img" aria-label={name}>
        {initials(name)}
      </div>
    );
  }

  return (
    <img
      className={className}
      style={style}
      src={activeSrc}
      alt={name}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => {
        if (useBig && bigSrc !== src) {
          // If the 'big' version fails, fall back to the original header image
          setUseBig(false);
        } else {
          setFailedSrc(true);
        }
      }}
    />
  );
}
