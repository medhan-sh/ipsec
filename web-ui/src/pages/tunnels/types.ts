import type { CandidateSet, VerdictItem, ClaimItem, FindingsDocument } from "@/api/types";

export interface NormalizedCandidateSet {
  sa_id: string;
  field: string;
  universeSize: number;
  survivors: string[];
  eliminated: [string, string][];
  indistinguishable: string[][];
  missingDirection: boolean;
}

export interface EliminationReasonGroup {
  id: string;
  reason: string;
  shortLabel: string;
  candidates: string[];
  count: number;
}

export interface EliminationStep {
  label: string;
  countEliminated: number;
  remainingCount: number;
  reasonText: string;
  groupId: string;
}

export function normalizeCandidateSet(
  cs: CandidateSet,
  doc?: FindingsDocument | null
): NormalizedCandidateSet {
  const sa_id = cs.sa_id || "spi:unspecified";
  const rawSurvivors: string[] =
    cs.survivors ?? (cs as unknown as { surviving?: string[] }).surviving ?? [];
  const eliminated: [string, string][] = Array.isArray(cs.eliminated)
    ? cs.eliminated.map((pair) => [String(pair[0]), String(pair[1])])
    : [];
  const indistinguishable: string[][] = Array.isArray(cs.indistinguishable)
    ? cs.indistinguishable.map((g) => (Array.isArray(g) ? g.map(String) : []))
    : [];

  const rawUniverseSize =
    (cs as unknown as { universe_size?: number }).universe_size ??
    cs.universe?.length ??
    rawSurvivors.length + eliminated.length;

  const universeSize = Math.max(rawUniverseSize, rawSurvivors.length + eliminated.length);

  // Missing direction detection
  let missingDirection = false;
  if (sa_id.includes("+none") || sa_id.endsWith("+none") || sa_id.includes("none")) {
    missingDirection = true;
  }
  if (doc?.gaps) {
    const hasGap = doc.gaps.some(
      (g) =>
        g.scope === sa_id &&
        (g.gap_kind === "asymmetric_routing" || g.rule_id === "tunnel_direction_missing")
    );
    if (hasGap) missingDirection = true;
  }
  if (doc?.coverage && doc.coverage.esp_tunnels_missing_a_direction > 0 && sa_id.includes("+none")) {
    missingDirection = true;
  }

  return {
    sa_id,
    field: cs.field || "esp.tunnel.cipher_suite",
    universeSize,
    survivors: rawSurvivors,
    eliminated,
    indistinguishable,
    missingDirection,
  };
}

export function groupEliminatedByReason(
  eliminated: [string, string][]
): EliminationReasonGroup[] {
  const map = new Map<string, string[]>();
  for (const [candidate, reason] of eliminated) {
    const list = map.get(reason) || [];
    list.push(candidate);
    map.set(reason, list);
  }

  const groups: EliminationReasonGroup[] = [];
  let idx = 0;
  for (const [reason, candidates] of map.entries()) {
    idx++;
    let shortLabel = `Criterion ${idx}`;
    const lower = reason.toLowerCase();
    if (lower.includes("null") || lower.includes("plaintext") || lower.includes("entropy")) {
      shortLabel = "NULL encryption check";
    } else if (lower.includes("gcd") || lower.includes("block size") || lower.includes("granularity") || lower.includes("delta")) {
      shortLabel = "Padding / GCD check";
    } else if (lower.includes("icv") || lower.includes("anchor") || lower.includes("salt")) {
      shortLabel = "ICV / anchor solver";
    } else if (lower.includes("proposal") || lower.includes("transform")) {
      shortLabel = "Proposal check";
    }

    groups.push({
      id: `reason-group-${idx}`,
      reason,
      shortLabel,
      candidates,
      count: candidates.length,
    });
  }

  return groups;
}

export function computeEliminationSteps(
  universeSize: number,
  groups: EliminationReasonGroup[]
): EliminationStep[] {
  const steps: EliminationStep[] = [];
  let current = universeSize;

  for (const group of groups) {
    current = Math.max(0, current - group.count);
    steps.push({
      label: group.shortLabel,
      countEliminated: group.count,
      remainingCount: current,
      reasonText: group.reason,
      groupId: group.id,
    });
  }

  return steps;
}

export function formatClaimDisplayValue(val: unknown): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "boolean") return val ? "true" : "false";
  if (typeof val === "number") return val.toLocaleString();
  if (typeof val === "string") return val;
  if (typeof val === "object") {
    const obj = val as Record<string, unknown>;
    const name = obj.name;
    const tid = obj.transform_id ?? obj.group_id;
    const klen = obj.key_length;
    if (name) {
      const parts: string[] = [];
      if (tid !== undefined) parts.push(`id ${tid}`);
      if (klen) parts.push(`${klen}-bit`);
      return parts.length > 0 ? `${name} (${parts.join(", ")})` : String(name);
    }
    return JSON.stringify(val);
  }
  return String(val);
}

export function getTunnelVerdicts(
  sa_id: string,
  verdicts: VerdictItem[]
): VerdictItem[] {
  return verdicts.filter((v) => v.sa_id === sa_id);
}

export function getIkeClaims(claims: ClaimItem[]): ClaimItem[] {
  return claims.filter((c) => {
    const f = c.field.toLowerCase();
    return (
      f.startsWith("ike.") ||
      f.startsWith("ike_sa.") ||
      f.startsWith("ikev1.") ||
      f.startsWith("ikev2.") ||
      f.startsWith("ike_sa_init.")
    );
  });
}
