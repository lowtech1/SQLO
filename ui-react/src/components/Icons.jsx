/**
 * Icons.jsx
 * Inline SVG icon components — consistent 16x16 stroke-based icons.
 * No external icon library dependency.
 */

/** @param {{size?: number, className?: string}} props */
export function Check({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polyline points="2.5,8.5 6.5,12.5 13.5,3.5" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function X({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <line x1="3" y1="3" x2="13" y2="13" />
      <line x1="13" y1="3" x2="3" y2="13" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function AlertTriangle({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M8 1.5 L14.5 13.5 H1.5 Z" />
      <line x1="8" y1="6" x2="8" y2="9.5" />
      <circle cx="8" cy="11.5" r="0.5" fill="currentColor" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function ChevronDown({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polyline points="4,6 8,10 12,6" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function ChevronUp({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polyline points="4,10 8,6 12,10" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Sparkles({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M8 0 L9 6 L16 8 L9 10 L8 16 L7 10 L0 8 L7 6 Z" opacity="0.8" />
      <circle cx="3" cy="3" r="1" opacity="0.5" />
      <circle cx="13" cy="13" r="1" opacity="0.5" />
      <circle cx="13" cy="3" r="0.8" opacity="0.4" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Copy({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" />
      <path d="M10.5 5.5 V3.5 a1 1 0 0 0-1-1 H3.5 a1 1 0 0 0-1 1 v6 a1 1 0 0 0 1 1 h2" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Play({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <polygon points="4,2 14,8 4,14" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Lock({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <rect x="3" y="7.5" width="10" height="7" rx="1.5" />
      <path d="M5.5 7.5 V5 a2.5 2.5 0 0 1 5 0 V7.5" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Database({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <ellipse cx="8" cy="3.5" rx="5" ry="1.5" />
      <path d="M3 3.5 V8 Q3 11 8 11 Q13 11 13 8 V3.5" />
      <path d="M3 8 Q3 11 8 11 Q13 11 13 8" />
      <path d="M3 11 Q3 14 8 14 Q13 14 13 11" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Zap({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <polygon points="9,1 4,9 8,9 7,15 12,7 8,7" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function ArrowRight({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <line x1="2" y1="8" x2="14" y2="8" />
      <polyline points="9,3 14,8 9,13" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Download({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M8 2 V10" />
      <polyline points="5,7.5 8,10.5 11,7.5" />
      <path d="M3 12 V13.5 H13 V12" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Grid({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <rect x="2" y="2" width="5" height="5" rx="1" />
      <rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" />
      <rect x="9" y="9" width="5" height="5" rx="1" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Loader({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      className={className}
      aria-hidden="true"
      style={{ animation: "spin 1s linear infinite" }}
    >
      <circle cx="8" cy="8" r="5.5" strokeOpacity="0.2" />
      <path d="M13.5 8 A5.5 5.5 0 0 0 8 2.5" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Send({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <line x1="2" y1="8" x2="14" y2="8" />
      <polyline points="10,2.5 14,8 10,13.5" />
      <line x1="2" y1="8" x2="7" y2="3" />
    </svg>
  );
}

/** @param {{size?: number, className?: string}} props */
export function Menu({ size = 16, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      className={className}
      aria-hidden="true"
    >
      <line x1="2" y1="4.5" x2="14" y2="4.5" />
      <line x1="2" y1="8" x2="14" y2="8" />
      <line x1="2" y1="11.5" x2="14" y2="11.5" />
    </svg>
  );
}
