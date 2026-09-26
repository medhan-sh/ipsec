"""test_runner.py — Tests for the TUI subprocess runner."""

import json
import sys
from pathlib import Path

from ipsec_analyzer.tui.runner import get_default_sibling_path, run_analysis


def test_get_default_sibling_path():
    assert get_default_sibling_path("captures/weberblog.pcap", ".findings.json") == Path("captures/weberblog.findings.json")
    assert get_default_sibling_path("captures/weberblog.pcap", ".report.html") == Path("captures/weberblog.report.html")
    assert get_default_sibling_path("foo.pcapng", ".findings.json") == Path("foo.findings.json")
    assert get_default_sibling_path("/tmp/test/foo.pcap", ".findings.json") == Path("/tmp/test/foo.findings.json")


def test_run_analysis_successful_invocation(tmp_path):
    pcap = tmp_path / "test.pcap"
    pcap.write_bytes(b"dummy")

    findings = tmp_path / "test.findings.json"
    findings_data = {
        "schema_version": "1.0",
        "capture": {"filename": "test.pcap", "packet_count": 10},
        "coverage": {"checks_total": 15},
    }
    findings.write_text(json.dumps(findings_data))

    # A python script that simulates successful analysis output
    custom_cmd = f"{sys.executable} -c \"print('Analysis done')\""
    result = run_analysis(pcap, custom_cmd=custom_cmd)

    assert result.success is True
    assert result.returncode == 0
    assert result.document is not None
    assert result.document.capture.filename == "test.pcap"
    assert result.document.coverage.checks_total == 15
    assert result.duration_s >= 0.0


def test_run_analysis_nonzero_exit(tmp_path):
    pcap = tmp_path / "test.pcap"
    pcap.write_bytes(b"dummy")

    custom_cmd = f"{sys.executable} -c \"import sys; sys.stderr.write('Fatal dissection error'); sys.exit(2)\""
    result = run_analysis(pcap, custom_cmd=custom_cmd)

    assert result.success is False
    assert result.returncode == 2
    assert "Fatal dissection error" in result.stderr
    assert result.document is None
    assert result.error_message is not None
    assert "2" in result.error_message


def test_run_analysis_missing_binary(tmp_path):
    pcap = tmp_path / "test.pcap"
    pcap.write_bytes(b"dummy")

    result = run_analysis(pcap, custom_cmd="non_existent_analyzer_command_xyz_123")
    assert result.success is False
    assert result.returncode == -1
    assert "not found" in result.error_message.lower()


def test_run_analysis_timeout(tmp_path):
    pcap = tmp_path / "test.pcap"
    pcap.write_bytes(b"dummy")

    custom_cmd = f"{sys.executable} -c \"import time; time.sleep(1.0)\""
    result = run_analysis(pcap, custom_cmd=custom_cmd, timeout_s=0.1)

    assert result.success is False
    assert result.returncode == -1
    assert "timed out" in result.error_message.lower()
