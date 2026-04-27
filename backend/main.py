import json
import random
import uuid
import time
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .room_manager import room_manager
from .types import Player, StoneColor, ChatMessage, RoomStatus, Position, Move, Room

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Alias for ASGI compatibility
socket_app = app

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}  # sid -> websocket
        self.sid_to_player: dict[str, dict] = {}  # sid -> {password, player_id}

    async def connect(self, websocket: WebSocket, sid: str):
        await websocket.accept()
        self.active_connections[sid] = websocket

    def disconnect(self, sid: str):
        self.active_connections.pop(sid, None)
        self.sid_to_player.pop(sid, None)

    async def send_personal(self, sid: str, data: dict):
        if sid in self.active_connections:
            await self.active_connections[sid].send_text(json.dumps(data))

    async def send_to_room(self, password: str, data: dict):
        for s, info in self.sid_to_player.items():
            if info["password"] == password and s in self.active_connections:
                await self.active_connections[s].send_text(json.dumps(data))


manager = ConnectionManager()


def generate_player_id() -> str:
    return f"player_{uuid.uuid4().hex[:12]}"


def generate_nickname() -> str:
    adjectives = [
        "快乐的", "聪明的", "勇敢的", "温柔的", "活泼的",
        "善良的", "可爱的", "机智的", "调皮的", "开心的",
        "认真的", "俏皮的", "沉稳的", "灵巧的", "淡定的",
        "乐观的", "勇敢的", "安静的", "爱笑的", "勤劳的"
    ]
    animals = [
        "小熊", "小兔", "小鹿", "小猫", "小狐狸",
        "小松鼠", "小企鹅", "小海豚", "小浣熊", "小熊猫",
        "小考拉", "小水獭", "小猫头鹰", "小刺猬", "小鲸鱼",
        "小柴犬", "小仓鼠", "小树懒", "小斑马", "小海豹"
    ]
    return f"{random.choice(adjectives)}{random.choice(animals)}"


@app.websocket("/ws/{sid}")
async def websocket_endpoint(websocket: WebSocket, sid: str):
    await websocket.accept()
    manager.active_connections[sid] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            event = msg.get("event")
            payload = msg.get("data")

            if event == "room:create":
                await handle_room_create(sid, payload)
            elif event == "room:join":
                await handle_room_join(sid, payload)
            elif event == "room:leave":
                await handle_room_leave(sid)
            elif event == "game:move":
                await handle_game_move(sid, payload)
            elif event == "game:pass":
                await handle_game_pass(sid)
            elif event == "game:resign":
                await handle_game_resign(sid)
            elif event == "chat:send":
                await handle_chat_send(sid, payload)
    except WebSocketDisconnect:
        await handle_disconnect(sid)


async def handle_disconnect(sid: str):
    if sid not in manager.sid_to_player:
        manager.disconnect(sid)
        return

    player_id = manager.sid_to_player[sid]["player_id"]
    password = manager.sid_to_player[sid]["password"]
    room_manager.set_player_connected(password, player_id, False)

    room = room_manager.get_room_by_password(password)
    if room:
        await manager.send_to_room(password, {"event": "room:player-left", "data": player_id})

    manager.disconnect(sid)


async def handle_room_create(sid: str, room_name: str):
    player_id = generate_player_id()
    player = Player(
        id=player_id,
        nickname=generate_nickname(),
        role="host",
        color=StoneColor.BLACK,
        isReady=False,
        connected=True,
        timeRemaining=20 * 60 * 1000,
        byoyomiCount=3,
        isInByoyomi=False,
    )

    room = room_manager.create_room(room_name, player)
    manager.sid_to_player[sid] = {"password": room.password, "player_id": player_id}

    await manager.send_personal(sid, {"event": "room:created", "data": room.model_dump()})


async def handle_room_join(sid: str, password: str):
    player_id = generate_player_id()
    player = Player(
        id=player_id,
        nickname=generate_nickname(),
        role="guest",
        color=StoneColor.WHITE,
        isReady=True,
        connected=True,
        timeRemaining=20 * 60 * 1000,
        byoyomiCount=3,
        isInByoyomi=False,
    )

    room, error = room_manager.join_room(password, player)

    if error:
        await manager.send_personal(sid, {"event": "error", "data": error})
        return

    if room:
        manager.sid_to_player[sid] = {"password": password, "player_id": player_id}

        guest = room.players.get("guest")
        host = room.players.get("host")

        room_manager.start_game(password)
        room_data = room.model_dump()

        # Send to guest (joining player)
        await manager.send_personal(sid, {"event": "room:game-start", "data": room_data})

        # Send to host if connected
        if host and host.connected:
            await manager.send_to_room(password, {"event": "room:game-start", "data": room_data})


async def handle_room_leave(sid: str):
    if sid not in manager.sid_to_player:
        return

    password = manager.sid_to_player[sid]["password"]
    player_id = manager.sid_to_player[sid]["player_id"]

    room_manager.leave_room(password, player_id)

    room = room_manager.get_room_by_password(password)
    if room:
        await manager.send_to_room(password, {"event": "room:player-left", "data": player_id})
        await manager.send_to_room(password, {"event": "room:updated", "data": room.model_dump()})
    else:
        await manager.send_personal(sid, {"event": "room:updated", "data": {"status": "deleted"}})

    manager.disconnect(sid)


async def handle_game_move(sid: str, position: dict):
    if sid not in manager.sid_to_player:
        await manager.send_personal(sid, {"event": "error", "data": "未加入房间"})
        return

    pos = Position(**position)
    password = manager.sid_to_player[sid]["password"]
    player_id = manager.sid_to_player[sid]["player_id"]

    move, error = room_manager.make_move(password, player_id, pos.x, pos.y)
    room = room_manager.get_room_by_password(password)

    if error:
        await manager.send_personal(sid, {"event": "error", "data": error})
        return

    if move and room:
        await manager.send_to_room(password, {
            "event": "game:move",
            "data": {"move": move.model_dump(), "room": room.model_dump()}
        })


async def handle_game_pass(sid: str):
    if sid not in manager.sid_to_player:
        return

    password = manager.sid_to_player[sid]["password"]
    player_id = manager.sid_to_player[sid]["player_id"]

    move, error = room_manager.pass_turn(password, player_id)
    room = room_manager.get_room_by_password(password)

    if move and room:
        if room.status == RoomStatus.FINISHED:
            await manager.send_to_room(password, {"event": "game:end", "data": room.model_dump()})
        else:
            await manager.send_to_room(password, {
                "event": "game:pass",
                "data": {"move": move.model_dump(), "room": room.model_dump()}
            })


async def handle_game_resign(sid: str):
    if sid not in manager.sid_to_player:
        return

    password = manager.sid_to_player[sid]["password"]
    player_id = manager.sid_to_player[sid]["player_id"]

    winner, error = room_manager.resign(password, player_id)
    room = room_manager.get_room_by_password(password)

    if winner and room:
        await manager.send_to_room(password, {"event": "game:resign", "data": winner})
        await manager.send_to_room(password, {"event": "game:end", "data": room.model_dump()})


async def handle_chat_send(sid: str, content: str):
    if sid not in manager.sid_to_player or not content.strip():
        return

    password = manager.sid_to_player[sid]["password"]
    player_id = manager.sid_to_player[sid]["player_id"]

    room = room_manager.get_room_by_password(password)
    if not room:
        return

    host = room.players.get("host")
    guest = room.players.get("guest")

    sender = None
    if host and host.id == player_id:
        sender = host
    elif guest and guest.id == player_id:
        sender = guest

    if not sender:
        return

    message = ChatMessage(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        senderId=player_id,
        senderNickname=sender.nickname,
        content=content.strip(),
        timestamp=int(time.time() * 1000),
    )

    await manager.send_to_room(password, {"event": "chat:message", "data": message.model_dump()})


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": time.time() * 1000}
