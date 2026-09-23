"""runner.py — Subprocess execution wrapper for the IPsec analyzer.

Preserves canonical execution through ./ipsec-analyze (which wraps Docker/TShark)
or allows custom execution via IPSEC_ANALYZE_CMD.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from ipsec_analyzer.tui.models import FindingsDocument


@dataclass(frozen=True)
class AnalysisRunResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    capture_path: Path
    findings_path: Path
    report_path: Path
    document: FindingsDocument | None = None
    error_message: str | None = None


def get_default_sibling_path(capture_path: str | Path, suffix: str) -> Path:
    p = Path(capture_path)
    stem = p.with_suffix("").name
    return p.parent / f"{stem}{suffix}"


def run_analysis(
    capture_path: str | Path,
    *,
    custom_cmd: str | None = None,
    cwd: str | Path | None = None,
    timeout_s: float = 300.0,
) -> AnalysisRunResult:
    """Executes the analyzer against a capture file in a subprocess.

    Defaults to `./ipsec-analyze <capture>`.
    Can be overridden via custom_cmd argument or `IPSEC_ANALYZE_CMD` env var.
    """
    pcap_path = Path(capture_path).resolve()
    findings_path = get_default_sibling_path(pcap_path, ".findings.json")
    report_path = get_default_sibling_path(pcap_path, ".report.html")

    cmd_override = custom_cmd or os.environ.get("IPSEC_ANALYZE_CMD")
    if cmd_override:
        parts = shlex.split(cmd_override) + [str(pcap_path)]
    else:
        # Canonical entry point: use ./ipsec-analyze (Docker wrapper) if Docker is available
        script_path = Path.cwd() / "ipsec-analyze"
        if shutil.which("docker") and script_path.is_file() and os.access(script_path, os.X_OK):
            parts = [str(script_path), str(pcap_path)]
        else:
            # Fallback to local python CLI when docker is not installed or ./ipsec-analyze is absent
            parts = [sys.executable, "-m", "ipsec_analyzer.cli", str(pcap_path)]


    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
            cwd=str(cwd) if cwd else str(Path.cwd()),
        )
        duration = round(time.perf_counter() - start_time, 2)
        stdout = proc.stdout
        stderr = proc.stderr
        rc = proc.returncode

        if rc != 0:
            return AnalysisRunResult(
                success=False,
                returncode=rc,
                stdout=stdout,
                stderr=stderr,
                duration_s=duration,
                capture_path=pcap_path,
                findings_path=findings_path,
                report_path=report_path,
                error_message=f"Analyzer exited with status {rc}.\n{stderr.strip() or stdout.strip()}",
            )

        # Process succeeded, load the emitted findings.json
        if not findings_path.is_file():
            return AnalysisRunResult(
                success=False,
                returncode=rc,
                stdout=stdout,
                stderr=stderr,
                duration_s=duration,
                capture_path=pcap_path,
                findings_path=findings_path,
                report_path=report_path,
                error_message=f"Analyzer completed successfully but '{findings_path.name}' was not created.",
            )

        doc = FindingsDocument.from_file(findings_path)
        return AnalysisRunResult(
            success=True,
            returncode=rc,
            stdout=stdout,
            stderr=stderr,
            duration_s=duration,
            capture_path=pcap_path,
            findings_path=findings_path,
            report_path=report_path,
            document=doc,
        )

    except subprocess.TimeoutExpired as exc:
        duration = round(time.perf_counter() - start_time, 2)
        return AnalysisRunResult(
            success=False,
            returncode=-1,
            stdout="",
            stderr=f"Timed out after {timeout_s}s",
            duration_s=duration,
            capture_path=pcap_path,
            findings_path=findings_path,
            report_path=report_path,
            error_message=f"Analysis timed out after {timeout_s} seconds.",
        )
    except FileNotFoundError as exc:
        duration = round(time.perf_counter() - start_time, 2)
        return AnalysisRunResult(
            success=False,
            returncode=-1,
            stdout="",
            stderr=str(exc),
            duration_s=duration,
            capture_path=pcap_path,
            findings_path=findings_path,
            report_path=report_path,
            error_message=f"Executable '{parts[0]}' not found. Ensure ./ipsec-analyze exists or set IPSEC_ANALYZE_CMD.",
        )
    except Exception as exc:
        duration = round(time.perf_counter() - start_time, 2)
        return AnalysisRunResult(
            success=False,
            returncode=-1,
            stdout="",
            stderr=str(exc),
            duration_s=duration,
            capture_path=pcap_path,
            findings_path=findings_path,
            report_path=report_path,
            error_message=f"Execution error: {exc}",
        )
