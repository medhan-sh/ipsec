/**
 * types.ts — Schema 1.0 TypeScript definitions for findings.json
 * Mirroring src/ipsec_analyzer/tui/models.py and core/claims.py.
 */

export type Tier =
  | "OBSERVED"
  | "INFERRED_SIDE_CHANNEL"
  | "INFERRED_IMPLEMENTATION_DEFAULT"
  | "ML_PREDICTION"
  | "NOT_OBSERVABLE";

export const TIER_ORDER: Record<string, number> = {
  OBSERVED: 5,
  INFERRED_SIDE_CHANNEL: 4,
  INFERRED_IMPLEMENTATION_DEFAULT: 3,
  ML_PREDICTION: 2,
  NOT_OBSERVABLE: 1,
};

export function tierOrder(tier: string): number {
  return TIER_ORDER[tier] ?? 0;
}

export function tierLabel(tier: string): string {
  switch (tier) {
    case "OBSERVED":
      return "observed";
    case "INFERRED_SIDE_CHANNEL":
      return "inferred (side-channel)";
    case "INFERRED_IMPLEMENTATION_DEFAULT":
      return "inferred (default)";
    case "ML_PREDICTION":
      return "ml prediction";
    case "NOT_OBSERVABLE":
      return "not observable";
    default:
      console.warn(`[Umbra] Unrecognized tier string: ${tier}`);
      return tier;
  }
}

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";

export interface CaptureMeta {
  filename: string;
  sha256: string;
  packet_count: number;
  duration_s: number;
  truncated: boolean;
}

export interface CoverageMeta {
  checks_total: number;
  checks_found: number;
  checks_passed: number;
  checks_assessable: number;
  checks_gap: number;
  packets_skipped: number;
  tshark_exit_clean: boolean;
  ike_sa_init_request_observed: boolean;
  ike_sa_init_response_observed: boolean;
  esp_tunnels_total: number;
  esp_tunnels_missing_a_direction: number;
  tshark_version: string;
}

export interface ClaimItem {
  field: string;
  value: unknown;
  tier: Tier | string;
  confidence: number | null;
  method: string;
  evidence: number[];
  caveats: string[];
}

export interface CandidateSet {
  field: string;
  universe: string[];
  eliminated: [string, string][];
  indistinguishable: string[][];
  survivors: string[];
  sa_id?: string;
}

export interface FindingItem {
  rule_id: string;
  severity: Severity | string;
  category?: string;
  title: string;
  tier: Tier | string;
  evidence: number[];
  scope: string;
  references?: string[];
  recommendation?: string;
}

export interface PassedCheckItem {
  rule_id: string;
  title?: string;
  tier: Tier | string;
  evidence?: number[];
  scope?: string;
}

export interface CoverageGapItem {
  rule_id: string;
  title?: string;
  gap_kind?: string;
  required_tier?: Tier | string;
  actual_tier?: Tier | string;
  reason?: string;
  scope?: string;
}

export interface VerdictItem {
  sa_id: string;
  predicate: string;
  ambiguous: boolean;
  confidence: number | null;
  basis_tier: Tier | string;
  basis: string;
  outcome: boolean | string;
  surviving_true: string[];
  surviving_false: string[];
}

export interface RuleMeta {
  title?: string;
  passed_title?: string;
  explanation?: string;
  recommendation?: string;
  references?: string[];
}

export interface FindingsDocument {
  schema_version: string;
  capture: CaptureMeta;
  coverage: CoverageMeta;
  claims: ClaimItem[];
  candidate_sets: CandidateSet[];
  findings: FindingItem[];
  passes: PassedCheckItem[];
  gaps: CoverageGapItem[];
  verdicts: VerdictItem[];
  rules: Record<string, RuleMeta>;
}

export interface CaptureItem {
  name: string;
  size: number;
  modified: string;
  has_findings: boolean;
  has_report: boolean;
  severity_counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
}

export interface SystemStatus {
  analyzer: string;
  analyzer_version: string;
  tshark: {
    available: boolean;
    version: string | null;
    error: string | null;
  };
  rules: number;
  rules_count: number;
  captures: number;
  captures_count: number;
  network: string;
}
