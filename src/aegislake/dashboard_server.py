"""Loopback-only, read-only dashboard explorer. Not an Internet-facing service."""

from __future__ import annotations

import hashlib
import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from aegislake.dashboard import MAX_BYTES, dashboard_page, read_snapshot


def navigation(text: str, key: str) -> str:
    def rewrite(match):
        route = urlsplit(html.unescape(match[1]))
        query = parse_qs(route.query)
        query["run"] = [key]
        url = urlunsplit(("", "", route.path, urlencode(query, doseq=True), route.fragment))
        return 'href="' + html.escape(url, quote=True) + '"'

    return re.sub(r'href="((?:report\.html|mitre\.html|dashboard\.html|attack-mapping\.json|dettect-techniques\.yaml)(?:[?#][^\"]*)?)"',
                  rewrite, text)


def catalog(root: Path) -> list[dict]:
    root = root.resolve()
    entries = []
    if not root.is_dir():
        return entries
    for directory in root.iterdir():
        if not directory.is_dir() or directory.is_symlink() or directory.name.endswith(".partial"):
            continue
        if not directory.resolve().is_relative_to(root):
            continue
        # A completed evaluation or scoring marker is required; half-written batches stay invisible.
        markers = [directory / "manifest.json", directory / "scoring.json"]
        if not any(marker.is_file() and not marker.is_symlink() for marker in markers):
            continue
        path = directory / "dashboard.json"
        if not path.is_file() or path.is_symlink():
            continue
        try:
            data = read_snapshot(path)
            entries.append({"key": hashlib.sha256(directory.name.encode()).hexdigest()[:20],
                            "path": directory, "modified": path.stat().st_mtime_ns,
                            "run": data["run"], "alerts": len(data["alerts"])})
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(entries, key=lambda item: (item["modified"], item["key"]), reverse=True)


def create_server(root: Path, port: int = 8767) -> ThreadingHTTPServer:
    """Serve an explicit run directory tree, never directory listings, logs or model artifacts."""
    if not 0 <= port <= 65535:
        raise ValueError("invalid port")

    class Handler(BaseHTTPRequestHandler):
        server_version = "AegisLakeLocal/1"

        def log_message(self, *_args):
            pass  # Do not log query strings, identities, or paths.

        def respond(self, status: int, body: bytes, content_type: str = "application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(body)

        def error_json(self, status: int, message: str):
            self.respond(status, json.dumps({"error": message}).encode())

        def do_GET(self):
            authorities = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            origin = self.headers.get("Origin")
            if self.headers.get("Host") not in authorities or (
                origin and origin not in {"http://" + value for value in authorities}
            ):
                self.error_json(403, "local origin required")
                return
            route = urlsplit(self.path)
            if route.path in ("/", "/dashboard.html"):
                self.respond(200, dashboard_page(api=True).encode(), "text/html")
                return
            entries = catalog(root)
            if route.path == "/api/runs":
                public = [{key: value for key, value in item.items() if key != "path"} for item in entries]
                self.respond(200, json.dumps({"runs": public}, allow_nan=False).encode())
                return
            match = re.fullmatch(r"/api/runs/([a-f0-9]{20})/dashboard", route.path)
            requested = match[1] if match else parse_qs(route.query).get("run", [""])[0]
            selected = next((item for item in entries if item["key"] == requested), None)
            if match and selected:
                try:
                    data = read_snapshot(selected["path"] / "dashboard.json")
                except (OSError, ValueError):
                    self.error_json(404, "dashboard batch unavailable")
                    return
                self.respond(200, json.dumps(data, allow_nan=False).encode())
                return
            allowed = {"/report.html", "/mitre.html", "/attack-mapping.json", "/dettect-techniques.yaml"}
            if route.path in allowed and selected:
                path = selected["path"] / route.path[1:]
                if path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_BYTES:
                    mime = "text/html" if path.suffix == ".html" else (
                        "application/yaml" if path.suffix == ".yaml" else "application/json")
                    content = path.read_bytes()
                    if path.suffix == ".html":
                        # Keep navigation inside this selected batch, including downloadable mapping files.
                        content = navigation(content.decode("utf-8"), selected["key"]).encode()
                    self.respond(200, content, mime)
                    return
            self.error_json(404, "dashboard resource not found")

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(root: Path, port: int = 8767) -> None:
    with create_server(root, port) as server:
        print(f"AegisLake dashboard: http://127.0.0.1:{server.server_port}/dashboard.html", flush=True)
        print("Local read-only batch explorer. Stop with Ctrl+C.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
