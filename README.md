
## 🕳️ BlackTunnel

BlackTunnel is a lightweight, open-source tunneling solution that allows you to expose a local backend + frontend server to the internet through a WebSocket tunnel.

### 📦 Components

* **BlackTunnel Server** – Handles WebSocket tunneling and client routing.
* **BlackTunnel Client** – Forwards local frontend/API traffic securely through the tunnel.

---

## 🚀 Features

* 🔐 Secure WebSocket tunneling
* 🖥️ Serves both frontend and backend from local machine
* 🌍 Exposes via a public server (can be hosted on Render/VPS)
* 📁 One-click portable client (`.exe` supported)

---

## 🧩 Server Setup (FastAPI)

```bash
pip install fastapi uvicorn websockets
uvicorn tunnel_server:app --host 0.0.0.0 --port 8000
```

> Server exposes WebSocket at `ws://<your-server>/ws`

---

## 🖥️ Client Usage

```bash
# With Python (requires websockets, aiohttp, requests)
python BlackTunner_Client.py --backend http://localhost:5000 --frontend ./template --tunnel ws://your-server/ws
```

Or compile with:

```bash
pyinstaller --onefile --icon=server.ico ^
  --paths=env/Lib/site-packages ^
  --hidden-import=websockets --hidden-import=aiohttp --hidden-import=requests ^
  BlackTunner_Client.py
```

Run the `.exe` from `dist/`.

---

## 💡 Notes

* The client opens a **proxy at `http://localhost:3333`** which mirrors both backend and static frontend.
* The server can be deployed on Render, VPS, or any cloud that supports FastAPI.
* Ideal for quick deployments, previews, or remote testing.

---

## ⚠️ Disclaimer

This tool is for development, testing, and educational use. Not intended for production-grade secure tunnels.

