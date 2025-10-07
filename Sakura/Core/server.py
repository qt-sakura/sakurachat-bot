import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from Sakura.Core.logging import logger
import socket

# HTTP SERVER FOR DEPLOYMENT
# A dummy HTTP handler for keep-alive purposes on deployment platforms
class DummyHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for keep-alive server"""

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Sakura bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress HTTP server logs
        pass


def start_server() -> None:
    """Start dummy HTTP server for deployment platforms"""
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        logger.info(f"🌐 Dummy server listening on port {port}")
        server.serve_forever()
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logger.warning(f"⚠️ Port {port} is already in use. Skipping dummy server startup.")
        else:
            logger.error(f"❌ Failed to start dummy server on port {port}: {e}")


def start_server_thread() -> None:
    """Start dummy server in background thread"""
    threading.Thread(target=start_server, daemon=True).start()
