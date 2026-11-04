// Football pitch markings, drawn as a faint overlay
export default function PitchBackground() {
  return (
    <svg className="pitch-lines" viewBox="0 0 1050 680" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="3">
        <rect x="25" y="25" width="1000" height="630" />
        <line x1="525" y1="25" x2="525" y2="655" />
        <circle cx="525" cy="340" r="91.5" />
        <rect x="25" y="138" width="165" height="404" />
        <rect x="25" y="248" width="55" height="184" />
        <rect x="860" y="138" width="165" height="404" />
        <rect x="970" y="248" width="55" height="184" />
        <path d="M190 266.9 A91.5 91.5 0 0 1 190 413.1" />
        <path d="M860 266.9 A91.5 91.5 0 0 0 860 413.1" />
        <path d="M40 25 A15 15 0 0 1 25 40" />
        <path d="M1010 25 A15 15 0 0 0 1025 40" />
        <path d="M25 640 A15 15 0 0 1 40 655" />
        <path d="M1025 640 A15 15 0 0 0 1010 655" />
      </g>
      <g fill="currentColor">
        <circle cx="525" cy="340" r="5" />
        <circle cx="135" cy="340" r="4" />
        <circle cx="915" cy="340" r="4" />
      </g>
    </svg>
  );
}
