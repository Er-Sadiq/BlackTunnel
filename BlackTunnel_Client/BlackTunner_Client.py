import asyncio
import websockets
import requests
import uuid
import ast
import os
import mimetypes
import argparse
import logging
from pathlib import Path
from aiohttp import web

# ------------------ Logger Setup ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("BlackTunnel")

# ------------------ CLI Setup ------------------

import argparse
import sys

def get_args():
    parser = argparse.ArgumentParser(description="🕳️ BlackTunnel Client")
    parser.add_argument("--backend", help="Local backend API URL (e.g. http://localhost:5000)")
    parser.add_argument("--frontend", help="Path to frontend folder (optional)", default="")
    parser.add_argument("--tunnel", help="Tunnel server WebSocket URL (e.g. ws://localhost:8765)")
    parser.add_argument("--port", help="Local proxy port", type=int, default=3333)

    # Parse only known args if no CLI args provided
    if len(sys.argv) > 1:
        args = parser.parse_args()
        if not args.backend or not args.tunnel:
            parser.error("Arguments --backend and --tunnel are required when using CLI.")
    else:
        # Interactive fallback
        args = parser.parse_args([])
        args.backend = input("🔌 Enter your backend server URL (e.g. http://localhost:5000): ").strip()
        args.frontend = input("📁 Enter path to frontend build folder (or leave empty if none): ").strip()
        args.tunnel = input("🌐 Enter tunnel server WebSocket URL (e.g. ws://localhost:8765): ").strip()
        args.port = 3333  # Default port

    return args

# Usage
args = get_args()

print(f"🆔 Backend URL       : {args.backend}")
print(f"📁 Frontend Path     : {args.frontend or 'None'}")
print(f"🌐 Tunnel Server     : {args.tunnel}")
print(f"📡 Local Proxy Port  : {args.port}")


CLIENT_ID = str(uuid.uuid4())
LOCAL_API_SERVER = args.backend.strip("/")
FRONTEND_PATH = args.frontend.strip()
TUNNEL_SERVER_ADDRESS = args.tunnel
LOCAL_PROXY_PORT = args.port

log.info(f"🆔 Client ID: {CLIENT_ID}")
log.info(f"📡 Proxy running at: http://localhost:{LOCAL_PROXY_PORT}")
if FRONTEND_PATH:
    log.info(f"🖼️ Serving frontend from: {FRONTEND_PATH}")
log.info(f"🌐 Tunnel server: {TUNNEL_SERVER_ADDRESS}")

# ------------------ Local Proxy (API + Frontend) ------------------

async def handle_request(request):
    path = request.path
    method = request.method
    headers = dict(request.headers)
    body = await request.read()

    # Serve static frontend
    if FRONTEND_PATH:
        static_file_path = Path(FRONTEND_PATH) / path.lstrip("/")
        index_file_path = Path(FRONTEND_PATH) / "index.html"

        if static_file_path.exists() and static_file_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(static_file_path))
            return web.Response(
                body=static_file_path.read_bytes(),
                content_type=mime_type or "application/octet-stream"
            )

        if index_file_path.exists():
            return web.Response(
                body=index_file_path.read_bytes(),
                content_type="text/html"
            )

    # Proxy API requests to backend
    try:
        target_url = LOCAL_API_SERVER + path
        if method.upper() == "POST":
            res = requests.post(target_url, headers=headers, data=body)
        else:
            res = requests.get(target_url, headers=headers)

        return web.Response(
            body=res.content,
            status=res.status_code,
            content_type=res.headers.get("Content-Type", "application/octet-stream")
        )

    except Exception as e:
        log.error(f"Backend error: {e}")
        return web.Response(text=f"Backend error: {e}", status=500)

async def start_local_proxy():
    app = web.Application()
    app.router.add_route('*', '/{tail:.*}', handle_request)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', LOCAL_PROXY_PORT)
    await site.start()
    log.info("🚀 Local proxy server started.")

# ------------------ Tunnel Connector ------------------

async def connect_tunnel():
    proxy_url = f"http://localhost:{LOCAL_PROXY_PORT}"
    while True:
        try:
            log.info("🔌 Connecting to tunnel server...")
            async with websockets.connect(TUNNEL_SERVER_ADDRESS) as websocket:
                await websocket.send(CLIENT_ID)
                log.info("🔗 Connected to tunnel server.")

                while True:
                    try:
                        raw_data = await websocket.recv()
                        req = ast.literal_eval(raw_data)

                        headers = req.get("headers", {})
                        body = req.get("body", "")
                        method = req.get("method", "GET")
                        path = req.get("path", "/")

                        url = proxy_url + path
                        log.info(f"➡️  Forwarding {method} request to {url}")

                        if method.upper() == "POST":
                            r = requests.post(url, headers=headers, data=body)
                        else:
                            r = requests.get(url, headers=headers)

                        await websocket.send(r.text)
                    except Exception as req_err:
                        error_msg = f"Request handling error: {req_err}"
                        log.error(error_msg)
                        await websocket.send(error_msg)

        except Exception as e:
            log.warning(f"🔌 Tunnel disconnected or failed: {e}")
            log.info("⏳ Retrying in 5 seconds...")
            await asyncio.sleep(5)

# ------------------ Main ------------------

async def main():
    await start_local_proxy()
    await connect_tunnel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.warning("🛑 Client interrupted. Exiting...")
