import { useState } from "react";
import { initials } from "../format";

// Player photo with an initials fallback if the image is missing or fails to load.
export default function Avatar({ src, name, size = 48, shape = "round" }) {
  const [failedSrc, setFailedSrc] = useState(null);
  const style = { width: size, height: size, fontSize: Math.max(11, size * 0.36) };
  const className = `avatar ${shape === "square" ? "avatar-square" : ""}`;
  if (!src || failedSrc === src) {
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
      src={src}
      alt={name}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setFailedSrc(src)}
    />
  );
}
