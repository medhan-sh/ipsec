import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");

// Load mock fixtures
const richMock = JSON.parse(
  fs.readFileSync(path.join(repoRoot, "web-ui/src/mocks/rich.mock.json"), "utf-8")
);
const goldenMock = JSON.parse(
  fs.readFileSync(path.join(repoRoot, "web-ui/src/mocks/golden.mock.json"), "utf-8")
);
const emptyMock = JSON.parse(
  fs.readFileSync(path.join(repoRoot, "web-ui/src/mocks/empty.mock.json"), "utf-8")
);

// Import our pure functions from types.ts
import {
  normalizeCandidateSet,
  groupEliminatedByReason,
  computeEliminationSteps,
  formatClaimDisplayValue,
  getTunnelVerdicts,
  getIkeClaims,
} from "../../web-ui/src/pages/tunnels/types.ts";

test("normalizeCandidateSet handles rich.mock.json (survivors & universe)", () => {
  const t1 = richMock.candidate_sets[0];
  const norm = normalizeCandidateSet(t1, richMock);

  assert.equal(norm.sa_id, "spi:0x3d713155+0xf918698d");
  assert.equal(norm.universeSize, 7);
  assert.equal(norm.survivors.length, 3);
  assert.equal(norm.eliminated.length, 4);
  assert.equal(norm.indistinguishable.length, 1);
  assert.equal(norm.missingDirection, false);
});

test("normalizeCandidateSet handles golden.mock.json (surviving & universe_size)", () => {
  const t1 = goldenMock.candidate_sets[0];
  const norm = normalizeCandidateSet(t1, goldenMock);

  assert.equal(norm.sa_id, "spi:0x3d713155+0xf918698d");
  assert.equal(norm.universeSize, 44);
  assert.equal(norm.survivors.length, 42);
  assert.equal(norm.eliminated.length, 2);
  assert.equal(norm.indistinguishable.length, 8);
  assert.equal(norm.missingDirection, false);
});

test("normalizeCandidateSet detects missing return direction", () => {
  const t3 = richMock.candidate_sets[2];
  const norm = normalizeCandidateSet(t3, richMock);

  assert.equal(norm.sa_id, "spi:0x55667788+none");
  assert.equal(norm.missingDirection, true);
});

test("groupEliminatedByReason groups candidates by exact reason text", () => {
  const t1 = richMock.candidate_sets[0];
  const groups = groupEliminatedByReason(t1.eliminated);

  assert.equal(groups.length, 3); // 4 eliminated pairs divided into 3 reasons

  // Find the ICV salt reason group which has 2 candidates
  const icvGroup = groups.find((g) => g.candidates.length === 2);
  assert.ok(icvGroup);
  assert.equal(icvGroup.shortLabel, "ICV / anchor solver");
  assert.deepEqual(icvGroup.candidates, ["AES-128-GCM-16", "AES-256-GCM-16"]);

  // Total count equals original eliminated length
  const total = groups.reduce((acc, g) => acc + g.count, 0);
  assert.equal(total, 4);
});

test("computeEliminationSteps yields sequential remaining counts ending in survivors", () => {
  const t1 = richMock.candidate_sets[0];
  const norm = normalizeCandidateSet(t1, richMock);
  const groups = groupEliminatedByReason(norm.eliminated);
  const steps = computeEliminationSteps(norm.universeSize, groups);

  assert.equal(steps.length, 3);
  // Step 1: 7 - 1 = 6
  assert.equal(steps[0].remainingCount, 6);
  // Step 2: 6 - 2 = 4
  assert.equal(steps[1].remainingCount, 4);
  // Step 3: 4 - 1 = 3 (matches 3 survivors!)
  assert.equal(steps[2].remainingCount, 3);
  assert.equal(steps[steps.length - 1].remainingCount, norm.survivors.length);
});

test("formatClaimDisplayValue formats various value types honestly", () => {
  assert.equal(formatClaimDisplayValue(null), "—");
  assert.equal(formatClaimDisplayValue(undefined), "—");
  assert.equal(formatClaimDisplayValue(true), "true");
  assert.equal(formatClaimDisplayValue(false), "false");
  assert.equal(formatClaimDisplayValue(1024), "1,024");
  assert.equal(formatClaimDisplayValue("IKEv2"), "IKEv2");

  // Transform object with name, group_id
  const dh = { name: "MODP-1024", group_id: 2 };
  assert.equal(formatClaimDisplayValue(dh), "MODP-1024 (id 2)");

  // Cipher transform with name, key_length
  const enc = { name: "3DES-CBC", key_length: 192 };
  assert.equal(formatClaimDisplayValue(enc), "3DES-CBC (192-bit)");
});

test("getTunnelVerdicts filters verdicts matching tunnel sa_id", () => {
  const v1 = getTunnelVerdicts("spi:0x3d713155+0xf918698d", richMock.verdicts);
  assert.equal(v1.length, 1);
  assert.equal(v1[0].predicate, "sixty_four_bit_block_cipher");
  assert.equal(v1[0].ambiguous, false);

  const v2 = getTunnelVerdicts("spi:0xaa11bb22+0xcc33dd44", richMock.verdicts);
  assert.equal(v2.length, 1);
  assert.equal(v2[0].predicate, "modern_aead_cipher");
  assert.equal(v2[0].ambiguous, true);

  const v3 = getTunnelVerdicts("spi:0xnonexistent", richMock.verdicts);
  assert.equal(v3.length, 0);
});

test("getIkeClaims extracts only IKE-related claims", () => {
  const ike = getIkeClaims(richMock.claims);
  assert.ok(ike.length > 0);
  for (const c of ike) {
    const f = c.field.toLowerCase();
    assert.ok(
      f.startsWith("ike.") ||
        f.startsWith("ike_sa.") ||
        f.startsWith("ikev1.") ||
        f.startsWith("ikev2.") ||
        f.startsWith("ike_sa_init.")
    );
  }
});

test("empty mock produces safe empty normalization", () => {
  const sets = emptyMock.candidate_sets.map((cs) => normalizeCandidateSet(cs, emptyMock));
  assert.equal(sets.length, 0);
});
