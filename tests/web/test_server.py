"""test_server.py — Unit tests for Umbra web server.

Uses Python standard library only (unittest, unittest.mock, http.client).
"""

from __future__ import annotations

import http.client
import json
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ipsec_analyzer.web.server import (
    ACTIVE_ANALYSES,
    ANALYSIS_LOCK,
    UmbraWebServer,
    create_server,
)


class TestUmbraWebServer(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="umbra_test_")
        self.captures_dir = Path(self.temp_dir) / "captures"
        self.captures_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir = Path(self.temp_dir) / "dist"

        # Use port 0 so the OS assigns an available ephemeral port
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
        with ANALYSIS_LOCK:
            ACTIVE_ANALYSES.clear()

    def request(
        self,
        method: str,
        path: str,
        body: bytes | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        req_headers = headers.copy() if headers else {}
        if body is not None and "Content-Length" not in req_headers:
            if isinstance(body, str):
                body = body.encode("utf-8")
            req_headers["Content-Length"] = str(len(body))

        conn.request(method, path, body=body, headers=req_headers)
        res = conn.getresponse()
        res_body = res.read()
        res_headers = {k: v for k, v in res.getheaders()}
        conn.close()
        return res.status, res_headers, res_body

    def test_status_endpoint(self) -> None:
        status, headers, body = self.request("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("default-src 'self'", headers.get("Content-Security-Policy", ""))
        data = json.loads(body.decode("utf-8"))
        self.assertIn("analyzer", data)
        self.assertIn("tshark", data)
        self.assertIn("rules", data)
        self.assertIn("captures", data)
        self.assertEqual(data.get("network"), "none")

    @patch("shutil.which", return_value=None)
    def test_status_survives_missing_tshark(self, mock_which: MagicMock) -> None:
        status, _, body = self.request("GET", "/api/status")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertFalse(data["tshark"]["available"])
        self.assertIn("tshark binary not found", data["tshark"]["error"])

    def test_captures_list_shape(self) -> None:
        # Create a mock pcap and sibling findings
        pcap_file = self.captures_dir / "sample.pcap"
        pcap_file.write_bytes(b"\x00" * 128)
        findings_file = self.captures_dir / "sample.findings.json"
        findings_file.write_text(
            json.dumps({
                "schema_version": "1.0",
                "findings": [
                    {"rule_id": "weak_dh", "severity": "HIGH"},
                    {"rule_id": "null_enc", "severity": "CRITICAL"},
                ],
            }),
            encoding="utf-8",
        )

        status, _, body = self.request("GET", "/api/captures")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        item = data[0]
        self.assertEqual(item["name"], "sample.pcap")
        self.assertEqual(item["size"], 128)
        self.assertTrue(item["has_findings"])
        self.assertFalse(item["has_report"])
        self.assertEqual(item["severity_counts"]["critical"], 1)
        self.assertEqual(item["severity_counts"]["high"], 1)
        self.assertEqual(item["severity_counts"]["low"], 0)

    def test_findings_retrieval_and_404(self) -> None:
        pcap_file = self.captures_dir / "test.pcap"
        pcap_file.write_bytes(b"\x00" * 32)
        findings_file = self.captures_dir / "test.findings.json"
        findings_content = {"schema_version": "1.0", "findings": []}
        findings_file.write_text(json.dumps(findings_content), encoding="utf-8")

        # Existing findings
        status, headers, body = self.request("GET", "/api/findings/test.pcap")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(json.loads(body.decode("utf-8")), findings_content)

        # Missing findings -> 404
        status, _, body = self.request("GET", "/api/findings/nonexistent.pcap")
        self.assertEqual(status, 404)
        err = json.loads(body.decode("utf-8"))
        self.assertIn("not found", err["message"].lower())

        # Path traversal rejection
        status, _, body = self.request("GET", "/api/findings/..%2Fsecret.pcap")
        self.assertEqual(status, 400)

    def test_report_sandboxed_csp(self) -> None:
        pcap_file = self.captures_dir / "tunnel.pcap"
        pcap_file.write_bytes(b"\x00" * 16)
        report_file = self.captures_dir / "tunnel.report.html"
        report_file.write_text("<!DOCTYPE html><html><body>Report</body></html>", encoding="utf-8")

        status, headers, body = self.request("GET", "/api/report/tunnel.pcap")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        # Critical security invariant: CSP sandbox prevents report execution as trusted app content
        self.assertIn("sandbox", headers.get("Content-Security-Policy", ""))
        self.assertIn("Report", body.decode("utf-8"))

    def test_upload_lifecycle_and_validation(self) -> None:
        # 1. Valid .pcap upload
        content = b"TEST_PCAP_STREAM_DATA"
        status, _, body = self.request("PUT", "/api/upload?name=upload_test.pcap", body=content)
        self.assertEqual(status, 201)
        res = json.loads(body.decode("utf-8"))
        self.assertEqual(res["name"], "upload_test.pcap")
        self.assertEqual(res["size"], len(content))
        self.assertTrue((self.captures_dir / "upload_test.pcap").is_file())

        # 2. Refuse duplicate without overwrite=1 -> 409 Conflict
        status, _, body = self.request("PUT", "/api/upload?name=upload_test.pcap", body=content)
        self.assertEqual(status, 409)
        self.assertIn("already exists", json.loads(body.decode("utf-8"))["message"].lower())

        # 3. Allow duplicate with overwrite=1 -> 201 Created
        new_content = b"UPDATED_CONTENT"
        status, _, body = self.request("PUT", "/api/upload?name=upload_test.pcap&overwrite=1", body=new_content)
        self.assertEqual(status, 201)
        self.assertEqual((self.captures_dir / "upload_test.pcap").read_bytes(), new_content)

        # 4. Reject bad extension (e.g. .exe, .sh) -> 400 Bad Request
        status, _, _ = self.request("PUT", "/api/upload?name=malicious.exe", body=content)
        self.assertEqual(status, 400)

        # 5. Reject path traversal attempt -> 400 Bad Request
        status, _, _ = self.request("PUT", "/api/upload?name=..%2Fevil.pcap", body=content)
        self.assertEqual(status, 400)

    def test_double_analyze_conflict(self) -> None:
        pcap_file = self.captures_dir / "active.pcap"
        pcap_file.write_bytes(b"\x00" * 32)

        # Simulate an ongoing analysis lock
        with ANALYSIS_LOCK:
            ACTIVE_ANALYSES.add("active.pcap")

        status, _, body = self.request(
            "POST",
            "/api/analyze",
            body=json.dumps({"capture": "active.pcap"}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 409)
        res = json.loads(body.decode("utf-8"))
        self.assertIn("already in progress", res["message"].lower())

    def test_static_fallback_when_dist_missing(self) -> None:
        status, _, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("UI not built", body.decode("utf-8"))
        self.assertIn("make web-build", body.decode("utf-8"))

    def test_spa_fallback_when_dist_present(self) -> None:
        self.static_dir.mkdir(parents=True, exist_ok=True)
        index_file = self.static_dir / "index.html"
        index_file.write_text("<!DOCTYPE html><html><body>Umbra SPA Shell</body></html>", encoding="utf-8")

        # Navigating to client route /app/overview should fall back to index.html
        status, _, body = self.request("GET", "/app/overview")
        self.assertEqual(status, 200)
        self.assertIn("Umbra SPA Shell", body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
