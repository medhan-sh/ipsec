import React from "react";

export const HeroVisual: React.FC = () => {
  return (
    <div
      aria-hidden="true"
      className="relative w-full h-48 sm:h-64 md:h-72 lg:h-80 overflow-hidden rounded-data border border-border-hairline bg-[#020503] flex items-center justify-center select-none"
    >
      {/* Background Architectural Grid */}
      <svg
        className="absolute inset-0 h-full w-full opacity-20 pointer-events-none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern
            id="hero-grid-pattern"
            width="32"
            height="32"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 32 0 L 0 0 0 32"
              fill="none"
              stroke="#17261d"
              strokeWidth="0.75"
            />
          </pattern>
          <linearGradient id="stream-fade" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00ff7f" stopOpacity="0" />
            <stop offset="35%" stopColor="#00ff7f" stopOpacity="0.4" />
            <stop offset="65%" stopColor="#00ff7f" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#00ff7f" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="beam-glow" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#00ff7f" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#00ff7f" stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#hero-grid-pattern)" />
      </svg>

      {/* Atmospheric Radial Vignette */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,255,127,0.06)_0%,rgba(2,5,3,0.85)_70%,rgba(0,0,0,1)_100%)] pointer-events-none" />

      {/* Center Evidence Topology Vectors */}
      <svg
        className="relative w-full h-full max-w-4xl px-4"
        viewBox="0 0 800 240"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Horizontal Baseline Axis */}
        <line
          x1="40"
          y1="120"
          x2="760"
          y2="120"
          stroke="#17261d"
          strokeWidth="1"
          strokeDasharray="4 4"
        />

        {/* Dynamic Trajectory Arc: Ingress Handshake */}
        <path
          d="M 60 120 Q 220 25 400 120"
          stroke="url(#stream-fade)"
          strokeWidth="1.5"
          className="animate-[pulse_4s_ease-in-out_infinite]"
        />

        {/* Dynamic Trajectory Arc: Egress ESP Tunnel */}
        <path
          d="M 400 120 Q 580 215 740 120"
          stroke="url(#stream-fade)"
          strokeWidth="1.5"
          className="animate-[pulse_4s_ease-in-out_infinite] [animation-delay:2s]"
        />

        {/* Coordinate Points & Observed Nodes */}
        {/* Node 1: Ingress Gateway */}
        <g transform="translate(60, 120)">
          <circle r="4" fill="#000000" stroke="#00ff7f" strokeWidth="1.5" />
          <circle r="1.5" fill="#00ff7f" />
          <text
            x="-8"
            y="-12"
            fill="#82a592"
            fontSize="9"
            fontFamily="monospace"
            letterSpacing="0.05em"
          >
            INIT:REQ
          </text>
        </g>

        {/* Node 2: SA Negotiation Invariant (Focal Node) */}
        <g transform="translate(400, 120)">
          <circle
            r="16"
            fill="none"
            stroke="#00ff7f"
            strokeWidth="0.75"
            strokeDasharray="2 3"
            className="animate-[spin_16s_linear_infinite]"
          />
          <circle r="6" fill="#000000" stroke="#00ff7f" strokeWidth="2" />
          <circle r="2.5" fill="#00ff7f" className="shadow-glow" />
          <text
            x="0"
            y="26"
            textAnchor="middle"
            fill="#d3ecdd"
            fontSize="10"
            fontWeight="bold"
            fontFamily="monospace"
            letterSpacing="0.08em"
          >
            OBSERVED SA INVARIANT
          </text>
          <text
            x="0"
            y="38"
            textAnchor="middle"
            fill="#5f8270"
            fontSize="8"
            fontFamily="monospace"
          >
            CONFIDENCE 1.0 · RFC 7296
          </text>
        </g>

        {/* Node 3: Tunnel Demux Ingress */}
        <g transform="translate(220, 72)">
          <circle r="3" fill="#040806" stroke="#00b35a" strokeWidth="1.5" />
          <text
            x="8"
            y="-4"
            fill="#5f8270"
            fontSize="8.5"
            fontFamily="monospace"
          >
            DH:GRP-14 (2048-bit)
          </text>
        </g>

        {/* Node 4: Side-channel GCD Estimator */}
        <g transform="translate(580, 168)">
          <circle r="3" fill="#040806" stroke="#ffd23f" strokeWidth="1.5" />
          <text
            x="8"
            y="12"
            fill="#ffd23f"
            fontSize="8.5"
            fontFamily="monospace"
          >
            ESP INFERENCE · GCD Δ=16
          </text>
        </g>

        {/* Node 5: Egress Gateway */}
        <g transform="translate(740, 120)">
          <circle r="4" fill="#000000" stroke="#00ff7f" strokeWidth="1.5" />
          <circle r="1.5" fill="#00ff7f" />
          <text
            x="-32"
            y="-12"
            fill="#82a592"
            fontSize="9"
            fontFamily="monospace"
            letterSpacing="0.05em"
          >
            INIT:RESP
          </text>
        </g>

        {/* Hairline Reticle Ticks */}
        <line x1="400" y1="80" x2="400" y2="100" stroke="#17261d" strokeWidth="1" />
        <line x1="400" y1="140" x2="400" y2="160" stroke="#17261d" strokeWidth="1" />
        <line x1="360" y1="120" x2="380" y2="120" stroke="#17261d" strokeWidth="1" />
        <line x1="420" y1="120" x2="440" y2="120" stroke="#17261d" strokeWidth="1" />
      </svg>

      {/* Edge Coordinates Indicators */}
      <div className="absolute top-2 left-3 font-mono text-[9px] text-text-tertiary select-none">
        PROVENANCE LATTICE // TOPOLOGY DISSECTION
      </div>
      <div className="absolute top-2 right-3 font-mono text-[9px] text-signal/60 select-none">
        PASSIVE PROBE: LIVE
      </div>
      <div className="absolute bottom-2 left-3 font-mono text-[9px] text-text-tertiary select-none">
        0x00000000 // WIRE ZERO-INTERFERENCE
      </div>
      <div className="absolute bottom-2 right-3 font-mono text-[9px] text-text-tertiary select-none">
        RFC 7296 / RFC 4303
      </div>
    </div>
  );
};
