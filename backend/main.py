import random
import uuid
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
from .room_manager import room_manager
from .types import Player, StoneColor, ChatMessage, RoomStatus

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, app)

socket_map: dict[str, dict] = {}


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


@sio.event
async def connect(sid, environ):
    print(f"客户端连接: {sid}")


@sio.event
async def disconnect(sid):
    if sid in socket_map:
        player_id = socket_map[sid]["player_id"]
        password = socket_map[sid]["password"]
        room_manager.set_player_connected(password, player_id, False)
        
        room = room_manager.get_room_by_password(password)
        if room:
            await sio.emit("room:player-left", player_id, to=room.password)
        
        del socket_map[sid]
    print(f"客户端断开: {sid}")


@sio.event
async def room_create(sid, room_name: str):
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
    socket_map[sid] = {"password": room.password, "player_id": player_id}
    await sio.enter_room(sid, room.password)
    
    await sio.emit("room:created", room.model_dump(), to=sid)


@sio.event
async def room_join(sid, password: str):
    player_id = generate_player_id()
    player = Player(
        id=player_id,
        nickname=generate_nickname(),
        role="guest",
        color=StoneColor.WHITE,
        isReady=False,
        connected=True,
        timeRemaining=20 * 60 * 1000,
        byoyomiCount=3,
        isInByoyomi=False,
    )

    room, error = room_manager.join_room(password, player)

    if error:
        await sio.emit("error", error, to=sid)
        return

    if room:
        socket_map[sid] = {"password": password, "player_id": player_id}
        await sio.enter_room(sid, password)
        
        guest = room.players.get("guest")
        host = room.players.get("host")
        
        await sio.emit("room:joined", room.model_dump(), guest.model_dump() if guest else None, to=sid)
        
        if host:
            await sio.emit("room:player-joined", guest.model_dump() if guest else None, to=room.password)


@sio.event
async def room_ready(sid):
    if sid not in socket_map:
        return
    
    password = socket_map[sid]["password"]
    player_id = socket_map[sid]["player_id"]
    
    both_ready = room_manager.player_ready(password, player_id)
    room = room_manager.get_room_by_password(password)
    
    if both_ready and room:
        room_manager.start_game(password)
        await sio.emit("room:game-start", room.model_dump(), to=room.password)
    elif room:
        await sio.emit("room:updated", room.model_dump(), to=room.password)


@sio.event
async def room_leave(sid):
    if sid not in socket_map:
        return
    
    password = socket_map[sid]["password"]
    player_id = socket_map[sid]["player_id"]
    
    room_manager.leave_room(password, player_id)
    
    room = room_manager.get_room_by_password(password)
    if room:
        await sio.emit("room:player-left", player_id, to=room.password)
        await sio.emit("room:updated", room.model_dump(), to=room.password)
    else:
        await sio.emit("room:updated", {"status": "deleted"}, to=sid)
    
    del socket_map[sid]


@sio.event
async def game_move(sid, position: dict):
    if sid not in socket_map:
        await sio.emit("error", "未加入房间", to=sid)
        return
    
    from .types import Position
    pos = Position(**position)
    
    password = socket_map[sid]["password"]
    player_id = socket_map[sid]["player_id"]
    
    move, error = room_manager.make_move(password, player_id, pos.x, pos.y)
    room = room_manager.get_room_by_password(password)
    
    if error:
        await sio.emit("error", error, to=sid)
        return
    
    if move and room:
        await sio.emit("game:move", move.model_dump(), room.model_dump(), to=room.password)


@sio.event
async def game_pass(sid):
    if sid not in socket_map:
        return
    
    password = socket_map[sid]["password"]
    player_id = socket_map[sid]["player_id"]
    
    move, error = room_manager.pass_turn(password, player_id)
    room = room_manager.get_room_by_password(password)
    
    if move and room:
        if room.status == RoomStatus.FINISHED:
            await sio.emit("game:end", room.model_dump(), to=room.password)
        else:
            await sio.emit("game:pass", move.model_dump(), room.model_dump(), to=room.password)


@sio.event
async def game_resign(sid):
    if sid not in socket_map:
        return
    
    password = socket_map[sid]["password"]
    player_id = socket_map[sid]["player_id"]
    
    winner, error = room_manager.resign(password, player_id)
    room = room_manager.get_room_by_password(password)
    
    if winner and room:
        await sio.emit("game:resign", winner, to=room.password)
        await sio.emit("game:end", room.model_dump(), to=room.password)


@sio.event
async def chat_send(sid, content: str):
    if sid not in socket_map or not content.strip():
        return
    
    password = socket_map[sid]["password"]
    player_id = socket_map[sid]["player_id"]
    
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
        timestamp=int(uuid.time.time() * 1000),
    )
    
    await sio.emit("chat:message", message.model_dump(), to=room.password)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": uuid.time.time() * 1000}