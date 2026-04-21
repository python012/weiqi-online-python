"""
围棋在线对弈平台 - Hugging Face Space 入口
直接从 backend 模块导入，保持代码复用
"""
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.main import (
    sio, room_manager,
    connect, disconnect, room_create, room_join, room_ready,
    room_leave, game_move, game_pass, game_resign, chat_send
)
from backend.types import Player, StoneColor, ChatMessage, RoomStatus

app = FastAPI(title="围棋在线对弈", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

socket_app = socketio.ASGIApp(sio, app)


@app.get("/")
async def root():
    return {"status": "ok", "service": "围棋在线对弈平台"}


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=7860)