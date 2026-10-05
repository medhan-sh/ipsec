"""server.py — Local HTTP server for Umbra Web UI.

Uses Python standard library only.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


ANALYSIS_LOCK = threading.Lock()
ACTIVE_ANALYSES: set[str] = set()

MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200 MB


def get_analyzer_version() -> str:
    """Returns package version without importing packaging dependencies."""
    try:
        pyproject_path = Path.cwd() / "pyproject.toml"
        if pyproject_path.is_file():
            text = pyproject_path.read_text(encoding="utf-8")
            m = re.search(r'version\s*=\s*"([^"]+)"', text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return "0.1.0"


def probe_tshark() -> dict[str, Any]:
    """Probes tshark availability and version."""
    tshark_bin = shutil.which("tshark")
    if not tshark_bin:
        return {
            "available": False,
            "version": None,
            "error": "tshark binary not found in PATH. Install Wireshark / tshark or run in Docker.",
        }
    try:
        proc = subprocess.run(
            [tshark_bin, "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0,
        )
        if proc.returncode == 0:
            first_line = proc.stdout.splitlines()[0] if proc.stdout else ""
            m = re.search(r"TShark\s*(?:\(Wireshark\))?\s*([\d\.]+)", first_line, re.IGNORECASE)
            version_str = m.group(1) if m else first_line.strip()
            return {
                "available": True,
                "version": version_str,
                "error": None,
            }
        return {
            "available": False,
            "version": None,
            "error": f"tshark probe exited with code {proc.returncode}: {proc.stderr.strip()}",
        }
    except Exception as e:
        return {
            "available": False,
            "version": None,
            "error": str(e),
        }


def count_loaded_rules() -> int:
    """Counts available rules from assessment rules.yaml without heavy imports."""
    try:
        rules_path = Path(__file__).resolve().parent.parent / "assessment" / "rules" / "rules.yaml"
        if not rules_path.is_file():
            rules_path = Path.cwd() / "src" / "ipsec_analyzer" / "assessment" / "rules" / "rules.yaml"
        if rules_path.is_file():
            text = rules_path.read_text(encoding="utf-8")
            # Count top-level list items with 'id:'
            matches = re.findall(r"^[ \t]*-[ \t]+id:\s*", text, re.MULTILINE)
            if matches:
                return len(matches)
    except Exception:
        pass
    return 15


def is_safe_child_path(base_dir: Path, target_path: Path) -> bool:
    """Verifies that target_path resolves strictly inside base_dir."""
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return resolved_target == resolved_base or resolved_base in resolved_target.parents
    except Exception:
        return False


def get_sibling_path(pcap_path: Path, suffix: str) -> Path:
    stem = pcap_path.with_suffix("").name
    return pcap_path.parent / f"{stem}{suffix}"


class UmbraRequestHandler(BaseHTTPRequestHandler):
    server_version = "UmbraWebServer/1.0"

    @property
    def captures_dir(self) -> Path:
        return getattr(self.server, "captures_dir", Path.cwd() / "captures")

    @property
    def static_dir(self) -> Path:
        return getattr(self.server, "static_dir", Path.cwd() / "web-ui" / "dist")

    def send_json(self, status_code: int, data: Any, extra_headers: dict[str, str] | None = None) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, status_code: int, message: str) -> None:
        self.send_json(status_code, {"error": True, "message": message}, extra_headers={"Connection": "close"})
        self.close_connection = True

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path)

        if path == "/api/status":
            self.handle_get_status()
        elif path == "/api/captures":
            self.handle_get_captures()
        elif path.startswith("/api/findings/"):
            capture_name = path[len("/api/findings/"):]
            self.handle_get_findings(capture_name)
        elif path.startswith("/api/report/"):
            capture_name = path[len("/api/report/"):]
            self.handle_get_report(capture_name)
        elif path.startswith("/api/"):
            self.send_error_json(HTTPStatus.NOT_FOUND, f"API endpoint not found: {path}")
        else:
            self.handle_static_or_spa(path)

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path)

        if path == "/api/analyze":
            self.handle_post_analyze()
        else:
            self.send_error_json(HTTPStatus.NOT_FOUND, f"API endpoint not found: {path}")

    def do_PUT(self) -> None:
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path)

        if path == "/api/upload":
            query_params = parse_qs(parsed_url.query)
            self.handle_put_upload(query_params)
        else:
            self.send_error_json(HTTPStatus.NOT_FOUND, f"API endpoint not found: {path}")

    def handle_get_status(self) -> None:
        tshark_info = probe_tshark()
        rules_count = count_loaded_rules()
        captures_count = 0
        if self.captures_dir.is_dir():
            captures_count = len([
                f for f in self.captures_dir.iterdir()
                if f.is_file() and f.suffix.lower() in {".pcap", ".pcapng"}
            ])

        response = {
            "analyzer": get_analyzer_version(),
            "analyzer_version": get_analyzer_version(),
            "tshark": tshark_info,
            "rules": rules_count,
            "rules_count": rules_count,
            "captures": captures_count,
            "captures_count": captures_count,
            "network": "none",
        }
        self.send_json(HTTPStatus.OK, response)

    def handle_get_captures(self) -> None:
        results = []
        if self.captures_dir.is_dir():
            for f in sorted(self.captures_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in {".pcap", ".pcapng"}:
                    findings_path = get_sibling_path(f, ".findings.json")
                    report_path = get_sibling_path(f, ".report.html")
                    has_findings = findings_path.is_file()
                    has_report = report_path.is_file()

                    severity_counts = {
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                        "info": 0,
                    }
                    if has_findings:
                        try:
                            content = json.loads(findings_path.read_text(encoding="utf-8"))
                            for finding in content.get("findings", []):
                                sev = str(finding.get("severity", "")).lower()
                                if sev in severity_counts:
                                    severity_counts[sev] += 1
                        except Exception:
                            pass

                    st = f.stat()
                    mod_time = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
                    results.append({
                        "name": f.name,
                        "size": st.st_size,
                        "modified": mod_time,
                        "has_findings": has_findings,
                        "has_report": has_report,
                        "severity_counts": severity_counts,
                    })

        self.send_json(HTTPStatus.OK, results)

    def handle_get_findings(self, capture_name: str) -> None:
        if not capture_name or "/" in capture_name or "\\" in capture_name or ".." in capture_name:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid capture name.")
            return

        target_pcap = self.captures_dir / capture_name
        if not is_safe_child_path(self.captures_dir, target_pcap):
            self.send_error_json(HTTPStatus.FORBIDDEN, "Access denied.")
            return

        findings_file = get_sibling_path(target_pcap, ".findings.json")
        if not findings_file.is_file():
            # Also try direct if capture_name already had or lacked suffix
            direct_file = self.captures_dir / (capture_name + ".findings.json")
            if direct_file.is_file():
                findings_file = direct_file

        if not findings_file.is_file():
            self.send_error_json(HTTPStatus.NOT_FOUND, f"Findings not found for capture: {capture_name}")
            return

        try:
            raw_data = findings_file.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw_data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'")
            self.end_headers()
            self.wfile.write(raw_data)
        except Exception as e:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Error reading findings: {e}")

    def handle_get_report(self, capture_name: str) -> None:
        if not capture_name or "/" in capture_name or "\\" in capture_name or ".." in capture_name:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid capture name.")
            return

        target_pcap = self.captures_dir / capture_name
        if not is_safe_child_path(self.captures_dir, target_pcap):
            self.send_error_json(HTTPStatus.FORBIDDEN, "Access denied.")
            return

        report_file = get_sibling_path(target_pcap, ".report.html")
        if not report_file.is_file():
            direct_file = self.captures_dir / (capture_name + ".report.html")
            if direct_file.is_file():
                report_file = direct_file

        if not report_file.is_file():
            self.send_error_json(HTTPStatus.NOT_FOUND, f"Report not found for capture: {capture_name}")
            return

        try:
            raw_data = report_file.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw_data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            # Strict CSP sandbox: untrusted report content cannot access cookies, parent frame, or local origin scripts
            self.send_header("Content-Security-Policy", "sandbox; default-src 'none'; style-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(raw_data)
        except Exception as e:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Error reading report: {e}")

    def handle_post_analyze(self) -> None:
        content_length_str = self.headers.get("Content-Length")
        if not content_length_str:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Missing Content-Length header.")
            return

        try:
            content_length = int(content_length_str)
            raw_body = self.rfile.read(content_length)
            body = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            self.send_error_json(HTTPStatus.BAD_REQUEST, f"Malformed JSON request: {e}")
            return

        capture_name = body.get("capture")
        if not capture_name or not isinstance(capture_name, str):
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Field 'capture' is required.")
            return

        if "/" in capture_name or "\\" in capture_name or ".." in capture_name:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid capture name.")
            return

        target_pcap = self.captures_dir / capture_name
        if not is_safe_child_path(self.captures_dir, target_pcap) or not target_pcap.is_file():
            self.send_error_json(HTTPStatus.NOT_FOUND, f"Capture file not found: {capture_name}")
            return

        with ANALYSIS_LOCK:
            if capture_name in ACTIVE_ANALYSES:
                self.send_error_json(
                    HTTPStatus.CONFLICT,
                    f"Analysis already in progress for capture: {capture_name}",
                )
                return
            ACTIVE_ANALYSES.add(capture_name)

        try:
            from ipsec_analyzer.tui.runner import run_analysis
            result = run_analysis(target_pcap)

            if not result.success:
                self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                    "success": False,
                    "returncode": result.returncode,
                    "duration": result.duration_s,
                    "message": result.error_message or "Analysis failed.",
                    "stderr": result.stderr,
                })
                return

            findings_data = None
            if result.findings_path and result.findings_path.is_file():
                try:
                    findings_data = json.loads(result.findings_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

            self.send_json(HTTPStatus.OK, {
                "success": True,
                "duration": result.duration_s,
                "findings": findings_data,
                "capture": capture_name,
            })
        except Exception as e:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Analysis runner failed: {e}")
        finally:
            with ANALYSIS_LOCK:
                ACTIVE_ANALYSES.discard(capture_name)

    def handle_put_upload(self, query_params: dict[str, list[str]]) -> None:
        def _abort(code: int, msg: str) -> None:
            try:
                cl_str = self.headers.get("Content-Length")
                if cl_str:
                    cl = int(cl_str)
                    if 0 < cl <= 10 * 1024 * 1024:
                        self.rfile.read(cl)
            except Exception:
                pass
            self.send_error_json(code, msg)

        name_list = query_params.get("name")
        if not name_list or not name_list[0].strip():
            _abort(HTTPStatus.BAD_REQUEST, "Query parameter 'name' is required.")
            return

        filename = name_list[0].strip()
        if "/" in filename or "\\" in filename or ".." in filename:
            _abort(HTTPStatus.BAD_REQUEST, "Invalid file name. Path separators are forbidden.")
            return

        ext = Path(filename).suffix.lower()
        if ext not in {".pcap", ".pcapng"}:
            _abort(HTTPStatus.BAD_REQUEST, "Only .pcap and .pcapng files are permitted.")
            return

        overwrite = query_params.get("overwrite", ["0"])[0] == "1"
        target_path = self.captures_dir / filename
        if not is_safe_child_path(self.captures_dir, target_path):
            _abort(HTTPStatus.FORBIDDEN, "Access denied.")
            return

        if target_path.exists() and not overwrite:
            _abort(
                HTTPStatus.CONFLICT,
                f"File '{filename}' already exists. Pass &overwrite=1 to overwrite.",
            )
            return

        content_length_str = self.headers.get("Content-Length")
        if not content_length_str:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Missing Content-Length header.")
            return

        try:
            content_length = int(content_length_str)
        except ValueError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header.")
            return

        if content_length > MAX_UPLOAD_SIZE:
            self.send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Upload exceeds 200 MB maximum size.")
            return

        self.captures_dir.mkdir(parents=True, exist_ok=True)
        temp_target = self.captures_dir / f".upload_{filename}_{int(time.time())}.tmp"

        bytes_read = 0
        chunk_size = 64 * 1024
        try:
            with open(temp_target, "wb") as f:
                while bytes_read < content_length:
                    to_read = min(chunk_size, content_length - bytes_read)
                    chunk = self.rfile.read(to_read)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_read += len(chunk)
                    if bytes_read > MAX_UPLOAD_SIZE:
                        raise ValueError("File exceeded upload size limit during streaming.")

            # Atomic commit
            temp_target.replace(target_path)
            self.send_json(HTTPStatus.CREATED, {
                "message": "Capture uploaded successfully.",
                "name": filename,
                "size": bytes_read,
            })
        except ValueError as ve:
            if temp_target.exists():
                temp_target.unlink()
            self.send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, str(ve))
        except Exception as e:
            if temp_target.exists():
                temp_target.unlink()
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Upload write failed: {e}")

    def handle_static_or_spa(self, request_path: str) -> None:
        if not self.static_dir.is_dir():
            msg = (
                "<!DOCTYPE html>\n"
                "<html>\n"
                "<head><title>Umbra Web UI</title>\n"
                "<style>body { background: #040806; color: #d3ecdd; font-family: monospace; padding: 40px; line-height: 1.6; }\n"
                "code { color: #00ff7f; }</style></head>\n"
                "<body>\n"
                "<h2>UI not built</h2>\n"
                "<p>Run <code>make web-build</code> (or <code>cd web-ui &amp;&amp; npm run build</code>) to build the web interface.</p>\n"
                "</body></html>"
            )
            data = msg.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'")
            self.end_headers()
            self.wfile.write(data)
            return

        rel_path = request_path.lstrip("/")
        target_file = (self.static_dir / rel_path).resolve()

        if is_safe_child_path(self.static_dir, target_file) and target_file.is_file():
            serve_path = target_file
        else:
            # SPA fallback to index.html
            serve_path = (self.static_dir / "index.html").resolve()

        if not serve_path.is_file():
            self.send_error_json(HTTPStatus.NOT_FOUND, "Resource not found.")
            return

        mime_type, _ = mimetypes.guess_type(str(serve_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            file_bytes = serve_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type or "json" in mime_type else mime_type)
            self.send_header("Content-Length", str(len(file_bytes)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline' data:")
            self.end_headers()
            self.wfile.write(file_bytes)
        except Exception as e:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Static serve error: {e}")


class UmbraWebServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler] = UmbraRequestHandler,
        captures_dir: Path | None = None,
        static_dir: Path | None = None,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.captures_dir = captures_dir or (Path.cwd() / "captures")
        static_default = os.environ.get("UMBRA_STATIC_DIR")
        self.static_dir = static_dir or (Path(static_default) if static_default else Path.cwd() / "web-ui" / "dist")


def create_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    captures_dir: Path | None = None,
    static_dir: Path | None = None,
) -> UmbraWebServer:
    return UmbraWebServer((host, port), UmbraRequestHandler, captures_dir=captures_dir, static_dir=static_dir)


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = create_server(host=host, port=port)
    if host in ("0.0.0.0", "::"):
        print(f"Umbra Web UI listening at http://localhost:{port}/ (http://127.0.0.1:{port}/) [bound to {host}:{port}] (captures: {server.captures_dir})")
    else:
        print(f"Umbra Web UI listening at http://{host}:{port}/ (captures: {server.captures_dir})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Umbra Web UI server.")
    finally:
        server.server_close()


def main() -> None:
    default_host = os.environ.get("UMBRA_WEB_HOST", "127.0.0.1")
    default_port = int(os.environ.get("UMBRA_WEB_PORT", "8765"))
    parser = argparse.ArgumentParser(description="Umbra Web UI local server")
    parser.add_argument("--host", default=default_host, help=f"Host address (default: {default_host})")
    parser.add_argument("--port", type=int, default=default_port, help=f"Port (default: {default_port})")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
