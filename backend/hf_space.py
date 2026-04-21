"""
围棋在线对弈平台 - Hugging Face Space 入口
支持长连接，适合 Socket.IO 实时通信
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from .main import (
    sio, app, socket_map, generate_player_id, generate_nickname,
    connect, disconnect, room_create, room_join, room_ready,
    room_leave, game_move, game_pass, game_resign, chat_send,
    room_manager
)
from .types import Player, StoneColor, ChatMessage, RoomStatus

socket_app = socketio.ASGIApp(sio, app)

async def lifespan(app: FastAPI):
    print("围棋服务启动 (Hugging Face Space)")
    yield
    print("围棋服务关闭")

app.router.lifespan_context = lifespan

__all__ = ["socket_app", "app", "sio"]