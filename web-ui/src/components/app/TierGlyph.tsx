import React from "react";
import { Tier } from "@/api/types";
import { cn } from "@/lib/utils";

interface TierGlyphProps {
  tier: Tier | string;
  size?: number;
  className?: string;
}

export const TierGlyph: React.FC<TierGlyphProps> = ({
  tier,
  size = 14,
  className,
}) => {
  const s = size;
  const r = (s - 2) / 2;
  const c = s / 2;

  switch (tier) {
    case "OBSERVED":
      // Solid disc with faint glow
      return (
        <svg
          width={s}
          height={s}
          viewBox={`0 0 ${s} ${s}`}
          className={cn("shrink-0 filter drop-shadow-[0_0_4px_rgba(0,255,127,0.4)]", className)}
          aria-label="Observed (certain)"
        >
          <circle cx={c} cy={c} r={r} fill="#00ff7f" />
        </svg>
      );

    case "INFERRED_SIDE_CHANNEL":
      // Three-quarter disc (75% filled)
      return (
        <svg
          width={s}
          height={s}
          viewBox={`0 0 ${s} ${s}`}
          className={cn("shrink-0", className)}
          aria-label="Inferred side-channel (75% luminance)"
        >
          <circle cx={c} cy={c} r={r} fill="none" stroke="#00b35a" strokeWidth="1" />
          <path
            d={`M ${c} ${c} L ${c} ${c - r} A ${r} ${r} 0 1 1 ${c - r} ${c} Z`}
            fill="#00cc66"
          />
        </svg>
      );

    case "INFERRED_IMPLEMENTATION_DEFAULT":
      // Half disc (55% filled)
      return (
        <svg
          width={s}
          height={s}
          viewBox={`0 0 ${s} ${s}`}
          className={cn("shrink-0", className)}
          aria-label="Inferred implementation default (55% luminance)"
        >
          <circle cx={c} cy={c} r={r} fill="none" stroke="#24402f" strokeWidth="1" />
          <path
            d={`M ${c} ${c - r} A ${r} ${r} 0 0 1 ${c} ${c + r} Z`}
            fill="#00994d"
          />
        </svg>
      );

    case "ML_PREDICTION":
      // Dashed ring (35% luminance, dashed outline)
      return (
        <svg
          width={s}
          height={s}
          viewBox={`0 0 ${s} ${s}`}
          className={cn("shrink-0", className)}
          aria-label="ML prediction (dashed ring)"
        >
          <circle
            cx={c}
            cy={c}
            r={r}
            fill="none"
            stroke="#00ff7f"
            strokeOpacity="0.35"
            strokeWidth="1.5"
            strokeDasharray="2 2"
          />
        </svg>
      );

    case "NOT_OBSERVABLE":
    default:
      // Empty hatched ring in tertiary text tone
      return (
        <svg
          width={s}
          height={s}
          viewBox={`0 0 ${s} ${s}`}
          className={cn("shrink-0", className)}
          aria-label="Not observable"
        >
          <circle
            cx={c}
            cy={c}
            r={r}
            fill="none"
            stroke="#5f8270"
            strokeWidth="1"
            strokeDasharray="1 2"
          />
          <line
            x1={c - r * 0.6}
            y1={c + r * 0.6}
            x2={c + r * 0.6}
            y2={c - r * 0.6}
            stroke="#5f8270"
            strokeWidth="1"
          />
        </svg>
      );
  }
};
