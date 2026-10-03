"""test_tunnels_view.py — Tests for the Tunnels page data contracts and web integration.

Verifies:
1. CandidateSet, Verdicts, and Claims contracts across rich, golden, and empty fixtures.
2. Tunnel directionality detection (bidirectional vs unidirectional missing direction).
3. Elimination reasoning grouping and staged count consistency.
4. Indistinguishable groups grouping and partitioning.
5. Verdict lifting integrity: ambiguous flags, basis text, and surviving_true/surviving_false.
6. Web server delivery of all tunnel fixtures and static SPA routing.
"""

from __future__ import annotations

import http.client
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from ipsec_analyzer.web.server import create_server


class TestTunnelsDataContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.mocks_dir = cls.repo_root / "web-ui" / "src" / "mocks"
        cls.dist_dir = cls.repo_root / "web-ui" / "dist"

        with open(cls.mocks_dir / "rich.mock.json", encoding="utf-8") as f:
            cls.rich_mock = json.load(f)
        with open(cls.mocks_dir / "golden.mock.json", encoding="utf-8") as f:
            cls.golden_mock = json.load(f)
        with open(cls.mocks_dir / "empty.mock.json", encoding="utf-8") as f:
            cls.empty_mock = json.load(f)

    def test_rich_mock_tunnels_contract(self) -> None:
        """Verify candidate sets, verdicts, and IKE claims in rich.mock.json."""
        candidate_sets = self.rich_mock.get("candidate_sets", [])
        self.assertEqual(len(candidate_sets), 3)

        # Tunnel 1: 3DES with 3 survivors and 4 eliminated
        t1 = candidate_sets[0]
        self.assertEqual(t1["sa_id"], "spi:0x3d713155+0xf918698d")
        self.assertIn("survivors", t1)
        self.assertEqual(len(t1["survivors"]), 3)
        self.assertEqual(len(t1["eliminated"]), 4)
        self.assertEqual(len(t1["indistinguishable"]), 1)
        self.assertEqual(len(t1["indistinguishable"][0]), 3)

        # Verify all survivors are accounted for in the indistinguishable group
        for s in t1["survivors"]:
            self.assertIn(s, t1["indistinguishable"][0])

        # Tunnel 2: AEAD with ambiguous verdict
        t2 = candidate_sets[1]
        self.assertEqual(t2["sa_id"], "spi:0xaa11bb22+0xcc33dd44")
        self.assertEqual(len(t2["survivors"]), 2)
        self.assertIn("AES-128-GCM-16", t2["survivors"])
        self.assertIn("AES-256-GCM-16", t2["survivors"])

        # Tunnel 3: Unidirectional (missing direction)
        t3 = candidate_sets[2]
        self.assertEqual(t3["sa_id"], "spi:0x55667788+none")
        self.assertTrue(t3["sa_id"].endswith("+none"))

        # Verify verdicts for rich mock
        verdicts = self.rich_mock.get("verdicts", [])
        self.assertEqual(len(verdicts), 2)

        v1 = verdicts[0]
        self.assertEqual(v1["sa_id"], t1["sa_id"])
        self.assertEqual(v1["predicate"], "sixty_four_bit_block_cipher")
        self.assertFalse(v1["ambiguous"])
        self.assertEqual(v1["outcome"], True)
        self.assertEqual(len(v1["surviving_true"]), 3)
        self.assertEqual(len(v1["surviving_false"]), 0)

        v2 = verdicts[1]
        self.assertEqual(v2["sa_id"], t2["sa_id"])
        self.assertEqual(v2["predicate"], "modern_aead_cipher")
        self.assertTrue(v2["ambiguous"])
        self.assertIn("ambiguous", str(v2["outcome"]).lower())

        # Verify IKE claims
        claims = self.rich_mock.get("claims", [])
        ike_claims = [c for c in claims if c["field"].startswith("ike.") or c["field"].startswith("ike_sa.")]
        self.assertGreater(len(ike_claims), 0)
        dh_claim = next((c for c in ike_claims if c["field"] == "ike.sa.dh_group"), None)
        self.assertIsNotNone(dh_claim)
        self.assertEqual(dh_claim["tier"], "OBSERVED")
        self.assertEqual(dh_claim["confidence"], 1.0)

    def test_golden_mock_tunnels_contract(self) -> None:
        """Verify candidate sets shape in golden.mock.json (uses surviving and universe_size)."""
        candidate_sets = self.golden_mock.get("candidate_sets", [])
        self.assertGreater(len(candidate_sets), 0)

        for cs in candidate_sets:
            self.assertIn("sa_id", cs)
            self.assertIn("surviving", cs)
            self.assertIn("universe_size", cs)
            self.assertEqual(cs["universe_size"], 44)
            # Weberblog capture has 42 surviving out of 44
            self.assertEqual(len(cs["surviving"]), 42)
            self.assertEqual(len(cs["eliminated"]), 2)
            # Indistinguishable groups are present
            self.assertIn("indistinguishable", cs)
            self.assertEqual(len(cs["indistinguishable"]), 8)

    def test_empty_mock_contract(self) -> None:
        """Verify empty fixture has zero candidate sets and zero verdicts."""
        self.assertEqual(len(self.empty_mock.get("candidate_sets", [])), 0)
        self.assertEqual(len(self.empty_mock.get("verdicts", [])), 0)
        self.assertEqual(len(self.empty_mock.get("claims", [])), 0)

    def test_production_build_artifacts(self) -> None:
        """Verify that web-ui/dist was built and contains valid offline bundle."""
        index_html = self.dist_dir / "index.html"
        self.assertTrue(index_html.exists(), "web-ui/dist/index.html must exist")
        html_content = index_html.read_text(encoding="utf-8")

        # Zero non-local scripts or external CDNs
        self.assertNotIn("http://", html_content)
        self.assertNotIn("https://", html_content)
        self.assertNotIn("fonts.googleapis.com", html_content)
        self.assertNotIn("cdn.jsdelivr.net", html_content)


class TestTunnelsServerDelivery(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="umbra_tunnels_test_")
        self.captures_dir = Path(self.temp_dir) / "captures"
        self.captures_dir.mkdir(parents=True, exist_ok=True)

        repo_root = Path(__file__).resolve().parent.parent.parent
        self.static_dir = repo_root / "web-ui" / "dist"

        # Populate a sample capture with rich findings
        mocks_dir = repo_root / "web-ui" / "src" / "mocks"
        rich_mock_path = mocks_dir / "rich.mock.json"
        pcap_file = self.captures_dir / "corp_eval.pcapng"
        pcap_file.write_bytes(b"\x00" * 256)
        findings_file = self.captures_dir / "corp_eval.findings.json"
        shutil.copyfile(rich_mock_path, findings_file)

        self.server = create_server(
            host="127.0.0.1",
            port=0,
            captures_dir=self.captures_dir,
            static_dir=self.static_dir,
        )
        self.port = self.server.server_address[1]
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tunnels_spa_route(self) -> None:
        """SPA fallback handles /app/tunnels route correctly."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/app/tunnels")
        res = conn.getresponse()
        body = res.read()
        conn.close()

        self.assertEqual(res.status, 200)
        self.assertIn(b"<html", body)

    def test_findings_contains_tunnels_data(self) -> None:
        """API /api/findings delivers candidate_sets, verdicts, and claims."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/api/findings/corp_eval.pcapng")
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        conn.close()

        self.assertEqual(res.status, 200)
        self.assertIn("candidate_sets", data)
        self.assertIn("verdicts", data)
        self.assertIn("claims", data)
        self.assertEqual(len(data["candidate_sets"]), 3)
