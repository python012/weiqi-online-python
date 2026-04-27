"""
围棋在线对弈平台 - Hugging Face Space 入口
当前版本使用 FastAPI 原生 WebSocket（非 python-socketio）
"""
from backend.main import app

socket_app = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=7860)