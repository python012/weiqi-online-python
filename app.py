"""
围棋在线对弈平台 - Hugging Face Space 入口
使用 FastAPI 原生 WebSocket
"""
from backend.main import app, socket_app, room_manager
from backend.types import Player, StoneColor, ChatMessage, RoomStatus

# app is already defined in backend.main with CORS middleware

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=7860)
