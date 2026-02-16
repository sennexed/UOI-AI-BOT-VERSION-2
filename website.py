"""Minimal status dashboard served via Python's standard library HTTP server."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Callable, Dict


class StatusWebsite:
    """Start and serve a simple HTML dashboard in a background thread."""

    def __init__(self, stats_provider: Callable[[], Dict[str, int | str]], host: str = "0.0.0.0", port: int = 8080) -> None:
        self.stats_provider = stats_provider
        self.host = host
        self.port = port

    def start(self) -> None:
        """Start the HTTP server in a daemon thread."""
        handler = self._build_handler(self.stats_provider)
        server = ThreadingHTTPServer((self.host, self.port), handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

    @staticmethod
    def _build_handler(stats_provider: Callable[[], Dict[str, int | str]]):
        class DashboardHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler naming)
                stats = stats_provider()
                html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='utf-8' />
<meta name='viewport' content='width=device-width, initial-scale=1' />
<title>UOI Discord AI Bot</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 2rem; background: #0f172a; color: #e2e8f0; }}
.card {{ max-width: 680px; background: #1e293b; padding: 1.5rem; border-radius: 12px; }}
h1 {{ margin-top: 0; }}
p {{ line-height: 1.5; }}
.kv {{ margin: 0.4rem 0; }}
small {{ color: #94a3b8; }}
</style>
</head>
<body>
<div class='card'>
<h1>UOI Discord AI Bot</h1>
<p class='kv'><strong>Status:</strong> Online</p>
<p class='kv'><strong>Daily token usage:</strong> {stats.get('daily_tokens', 0)}</p>
<p class='kv'><strong>Lifetime token usage:</strong> {stats.get('total_tokens', 0)}</p>
<p class='kv'><strong>UTC reset time:</strong> 00:00 UTC</p>
<small>Last reset date: {stats.get('last_reset_date', '')}</small>
</div>
</body>
</html>"""
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        return DashboardHandler
      
