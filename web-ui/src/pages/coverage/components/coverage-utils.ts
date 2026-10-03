/**
 * coverage-utils.ts — Helpers and human labels for coverage accounting and gap kinds.
 * Mirroring output/report.py and assessment/engine.py.
 */

export const GAP_KIND_LABELS: Record<string, string> = {
  structurally_unobservable: "never observable passively",
  not_implemented: "not parsed by this build",
  not_observed_in_capture: "not observed in this capture",
  not_observable: "not observable on wire",
  missing_exchange: "exchange not captured",
  asymmetric_routing: "asymmetric routing / unobserved return",
};

export const GAP_KIND_DESCRIPTIONS: Record<string, string> = {
  structurally_unobservable:
    "No passive observer can ever determine this. The information never appears on the wire in any form. Must be verified against endpoint configuration.",
  not_implemented:
    "Observable in principle on the wire, but this build does not parse what it requires. A software roadmap limitation, not an IPsec limit.",
  not_observed_in_capture:
    "The analysis method exists, but this capture did not contain enough signal. A longer or different capture of the tunnel could answer it.",
  missing_exchange:
    "The required handshake or rekey exchange was outside the capture time window.",
  asymmetric_routing:
    "Only one direction of traffic was observed. The return path traffic was routed over another path.",
};

export function getGapKindLabel(kind?: string): string {
  if (!kind) return "unspecified gap";
  return GAP_KIND_LABELS[kind] || kind.replace(/_/g, " ");
}

export function getGapKindDescription(kind?: string): string {
  if (!kind) return "";
  return GAP_KIND_DESCRIPTIONS[kind] || "";
}
