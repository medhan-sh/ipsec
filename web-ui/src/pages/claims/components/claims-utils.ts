import { ClaimItem, Tier } from "@/api/types";

/**
 * One-sentence tier explanations matching core/claims.py and output/report.py.
 * The central provenance lattice of Umbra.
 */
export const TIER_EXPLANATIONS: Record<string, string> = {
  OBSERVED:
    "Read straight off the wire from a field the protocol sends in the clear, dissected by tshark. Confidence at this tier is always exactly 1.0 — if something isn't certain, it isn't observed.",
  INFERRED_SIDE_CHANNEL:
    "Worked out from things the encryption cannot hide — chiefly the sizes of packets, and the timing between them. Subject to identifying the right packets to measure.",
  INFERRED_IMPLEMENTATION_DEFAULT:
    "Assumed from what a particular vendor's stack normally does, once that vendor has been identified. Sits below side-channel inference because a measurement beats an assumption.",
  ML_PREDICTION:
    "Output of a statistical model. May only rank possibilities that deterministic engines have already admitted; can never reintroduce one ruled out by arithmetic.",
  NOT_OBSERVABLE:
    "Absence of a claim, not a weak claim. Either nothing on the wire could ever answer this question, or this capture lacked the signal. Carries no value at all.",
};

export const ALL_TIERS: Tier[] = [
  "OBSERVED",
  "INFERRED_SIDE_CHANNEL",
  "INFERRED_IMPLEMENTATION_DEFAULT",
  "ML_PREDICTION",
  "NOT_OBSERVABLE",
];

/**
 * Format a claim value for display in the table or summary.
 * If NOT_OBSERVABLE, strictly return "—".
 */
export function formatClaimValue(value: unknown, tier: Tier | string): string {
  if (tier === "NOT_OBSERVABLE" || value === null || value === undefined) {
    return "—";
  }

  if (typeof value === "object") {
    const obj = value as Record<string, any>;
    if (obj.name) {
      const extra: string[] = [];
      if (obj.group_id !== undefined) extra.push(`group ${obj.group_id}`);
      if (obj.transform_id !== undefined) extra.push(`id ${obj.transform_id}`);
      if (obj.key_length !== undefined) extra.push(`${obj.key_length}-bit`);
      const extraStr = extra.length > 0 ? ` (${extra.join(", ")})` : "";
      return `${obj.name}${extraStr}`;
    }
    if (Array.isArray(value)) {
      return value.map(String).join(", ");
    }
    return JSON.stringify(value);
  }

  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }

  return String(value);
}

/**
 * Format full claim value for drawer (pretty-printed JSON).
 */
export function getFormattedClaimJson(value: unknown, tier: Tier | string): string {
  if (tier === "NOT_OBSERVABLE") {
    return "null (NOT_OBSERVABLE claims carry no value)";
  }
  if (value === null || value === undefined) {
    return "null";
  }
  return JSON.stringify(value, null, 2);
}

export interface GroupedClaim {
  field: string;
  claims: ClaimItem[];
  occurrences: number;
  distinctValues: string[];
  tiers: (Tier | string)[];
  uniqueEvidence: number[];
  totalCaveatsCount: number;
  hasNotObservable: boolean;
  hasObserved: boolean;
}

/**
 * Collapse claims by field name into grouped rows.
 */
export function groupClaimsByField(claims: ClaimItem[]): GroupedClaim[] {
  const map = new Map<string, ClaimItem[]>();

  for (const claim of claims) {
    const list = map.get(claim.field) || [];
    list.push(claim);
    map.set(claim.field, list);
  }

  const result: GroupedClaim[] = [];

  for (const [field, group] of map.entries()) {
    const distinctVals = Array.from(
      new Set(group.map((c) => formatClaimValue(c.value, c.tier)))
    );
    const tiers = Array.from(new Set(group.map((c) => c.tier)));
    const evSet = new Set<number>();
    let caveatsCount = 0;

    for (const c of group) {
      c.evidence?.forEach((f) => evSet.add(f));
      caveatsCount += c.caveats?.length || 0;
    }

    result.push({
      field,
      claims: group,
      occurrences: group.length,
      distinctValues: distinctVals,
      tiers,
      uniqueEvidence: Array.from(evSet).sort((a, b) => a - b),
      totalCaveatsCount: caveatsCount,
      hasNotObservable: tiers.includes("NOT_OBSERVABLE"),
      hasObserved: tiers.includes("OBSERVED"),
    });
  }

  return result;
}
