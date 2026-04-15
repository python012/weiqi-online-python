from pydantic import BaseModel
from enum import Enum
from typing import Optional


class StoneColor(str, Enum):
    BLACK = "black"
    WHITE = "white"


class PlayerRole(str, Enum):
    HOST = "host"
    GUEST = "guest"
    SPECTATOR = "spectator"


class RoomStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


class Position(BaseModel):
    x: int
    y: int


class Move(BaseModel):
    position: Position
    color: StoneColor
    moveNumber: int
    timestamp: int
    capturedStones: list[Position] = []


class Player(BaseModel):
    id: str
    nickname: str
    role: PlayerRole
    color: Optional[StoneColor] = None
    isReady: bool = False
    connected: bool = True
    timeRemaining: int = 1200000
    byoyomiCount: int = 3
    isInByoyomi: bool = False


class Room(BaseModel):
    id: str
    name: str
    password: str
    status: RoomStatus = RoomStatus.WAITING
    players: dict = {}
    spectators: list[Player] = []
    board: list[list[Optional[StoneColor]]]
    moves: list[Move] = []
    currentTurn: StoneColor = StoneColor.BLACK
    koPosition: Optional[Position] = None
    lastMove: Optional[Move] = None
    winner: Optional[StoneColor] = None
    result: str = ""
    startedAt: Optional[int] = None


class ChatMessage(BaseModel):
    id: str
    senderId: str
    senderNickname: str
    content: str
    timestamp: int


GAME_CONFIG = {
    "BOARD_SIZE": 19,
    "BASE_TIME": 20 * 60 * 1000,
    "BYOYOMI_TIME": 60 * 1000,
    "BYOYOMI_COUNT": 3,
}


def generate_room_password(length: int = 5) -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    import random
    return "".join(random.choice(chars) for _ in range(length))


def create_empty_board(size: int = 19) -> list[list[Optional[StoneColor]]]:
    return [[None] * size for _ in range(size)]