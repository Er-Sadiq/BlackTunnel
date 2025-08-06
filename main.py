from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()
active_clients: dict[str, WebSocket] = {}


@app.get('/ping')
def health_check():
    return{"message":"pong"}


@app.websocket("/{client_id}")
async def ws_client(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_clients[client_id] = websocket
    try:
        while True:
            # keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_clients.pop(client_id, None)

@app.api_route("/{client_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_to_client(client_id: str, path: str, request: Request):
    ws = active_clients.get(client_id)
    if not ws:
        return JSONResponse(status_code=404, content={"error": "Tunnel not active"})

    req_payload = {
        "method": request.method,
        "path": f"/{path}",
        "headers": dict(request.headers),
        "body": (await request.body()).decode("utf-8", errors="ignore")
    }
    await ws.send_json(req_payload)

    try:
        response = await ws.receive_json()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Client disconnected: {e}"})

    return JSONResponse(status_code=response.get("status", 200),
                         content=response.get("content", ""),
                         headers=response.get("headers", {}))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
