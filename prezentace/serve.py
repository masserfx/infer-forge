#!/usr/bin/env python3
"""
inferbox — Dynamic Architecture Server
Serves the interactive flowchart and re-generates graph data on demand.

Usage:
    python3 prezentace/serve.py [--port 8080]

Features:
    - Serves static HTML/JS/CSS
    - GET /api/refresh — re-runs analyze_codebase.py and returns fresh JSON
    - GET / — serves index.html
"""

import http.server
import json
import subprocess
import sys
from functools import partial
from pathlib import Path
from urllib.parse import urlparse


PORT = 8080
DIR = Path(__file__).resolve().parent
ANALYZER = DIR / "analyze_codebase.py"

for i, arg in enumerate(sys.argv[1:]):
    if arg == "--port" and i + 2 < len(sys.argv):
        PORT = int(sys.argv[i + 2])


def make_handler(directory: str):
    """Factory to create handler class with directory baked in."""

    class FlowchartHandler(http.server.SimpleHTTPRequestHandler):
        """HTTP handler with API endpoint for refreshing graph data."""

        def __init__(self, *args, **kwargs):
            kwargs["directory"] = directory
            super().__init__(*args, **kwargs)

        def do_GET(self):
            parsed = urlparse(self.path)

            if parsed.path == "/api/refresh":
                self.handle_refresh()
                return

            super().do_GET()

        def handle_refresh(self):
            """Re-run the analyzer and return fresh JSON."""
            try:
                result = subprocess.run(
                    [sys.executable, str(ANALYZER)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(DIR.parent),
                )

                if result.returncode != 0:
                    self.send_error_json(500, f"Analyzer failed: {result.stderr}")
                    return

                json_path = DIR / "graph_data.json"
                if not json_path.exists():
                    self.send_error_json(500, "graph_data.json not generated")
                    return

                data = json_path.read_text(encoding="utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(data.encode("utf-8"))

            except subprocess.TimeoutExpired:
                self.send_error_json(504, "Analyzer timed out")
            except Exception as e:
                self.send_error_json(500, str(e))

        def send_error_json(self, code: int, message: str):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": message}).encode("utf-8"))

        def log_message(self, fmt, *args):
            msg = fmt % args if args else fmt
            if "/api/refresh" in msg:
                print(f"\033[36m[REFRESH]\033[0m {msg}")
            else:
                print(f"\033[32m[REQ]\033[0m {msg}")

    return FlowchartHandler


def main():
    print(f"\033[1;34minferbox Architecture Server\033[0m")
    print(f"Generating initial graph data...")
    subprocess.run(
        [sys.executable, str(ANALYZER)],
        cwd=str(DIR.parent),
    )

    handler_class = make_handler(str(DIR))
    server = http.server.HTTPServer(("0.0.0.0", PORT), handler_class)
    print(f"\n\033[1;32mServer running at:\033[0m")
    print(f"  \033[4mhttp://localhost:{PORT}\033[0m")
    print(f"\nEndpoints:")
    print(f"  GET /            — Interactive flowchart")
    print(f"  GET /api/refresh — Re-analyze codebase & refresh data")
    print(f"\nPress Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
