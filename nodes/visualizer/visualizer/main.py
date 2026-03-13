"""MJPEG Server node with automatic browser opening and debug logging."""

import http.server
import threading
import webbrowser
import time
import logging
from typing import Optional
from dora import Node, DoraStatus

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("visualizer")

SHARED_FRAME: Optional[bytes] = None
FRAME_LOCK = threading.Lock()

class MJPEGHandler(http.server.BaseHTTPRequestHandler):
    """Handles MJPEG streaming requests."""
    def do_GET(self) -> None:
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    with FRAME_LOCK:
                        if SHARED_FRAME is None: continue
                        frame = SHARED_FRAME
                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame + b'\r\n')
            except (ConnectionResetError, BrokenPipeError):
                logger.debug("Client disconnected.")

def open_browser():
    """Wait for the server to start, then open the browser."""
    time.sleep(2)  # Give the server time to bind the port
    url = "http://localhost:8080"
    logger.info(f"Opening browser at {url}")
    webbrowser.open(url)

def main():
    node = Node()
    
    # 1. Start HTTP Server
    server = http.server.ThreadingHTTPServer(('0.0.0.0', 8080), MJPEGHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    
    # 2. Start Auto-Browser Opener
    threading.Thread(target=open_browser, daemon=True).start()
    
    logger.info("Visualizer node started.")

    for event in node:
        if event["type"] == "INPUT" and event["id"] == "image":
            global SHARED_FRAME
            with FRAME_LOCK:
                SHARED_FRAME = bytes(event["value"])
            logger.debug(f"Received frame: {len(SHARED_FRAME)} bytes")

    return DoraStatus.CONTINUE

if __name__ == "__main__":
    main()