const base = {
  width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true,
};

export function BallIcon(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="10" />
      <polygon points="12,8 15.8,10.8 14.35,15.2 9.65,15.2 8.2,10.8" />
      <path d="M12 8V2M15.8 10.8l5.7-1.9M14.35 15.2l3.55 4.9M9.65 15.2L6.1 20.1M8.2 10.8L2.5 8.9" />
    </svg>
  );
}

export function VersusIcon(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="8.5" cy="12" r="6" />
      <circle cx="15.5" cy="12" r="6" />
    </svg>
  );
}

export function ChartIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </svg>
  );
}

export function CalendarIcon(props) {
  return (
    <svg {...base} {...props}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </svg>
  );
}

export function GapIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M4 8h16M4 16h16M8 4l-4 4 4 4M16 12l4 4-4 4" />
    </svg>
  );
}

export function SearchIcon(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-4-4" />
    </svg>
  );
}
