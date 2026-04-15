from typing import Optional
from .types import (
    Room, Player, StoneColor, Move, Position, 
    RoomStatus, create_empty_board
)
from .game_engine import validate_move, make_move, calculate_score
import uuid


class RoomManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self.password_map: dict[str, str] = {}

    def create_room(self, name: str, host: Player) -> Room:
        room_id = str(uuid.uuid4())
        password = self._generate_password()
        
        host.color = StoneColor.BLACK
        host.timeRemaining = 20 * 60 * 1000
        host.byoyomiCount = 3
        host.isInByoyomi = False
        
        room = Room(
            id=room_id,
            name=name,
            password=password,
            status=RoomStatus.WAITING,
            players={"host": host, "guest": None},
            spectators=[],
            board=create_empty_board(),
            moves=[],
            currentTurn=StoneColor.BLACK,
            koPosition=None,
            lastMove=None,
            winner=None,
            result="",
            startedAt=None,
        )
        
        self.rooms[room_id] = room
        self.password_map[password] = room_id
        return room

    def join_room(self, password: str, player: Player, spectate: bool = False) -> tuple[Optional[Room], Optional[str]]:
        room_id = self.password_map.get(password.upper())
        if not room_id:
            return None, "房间不存在"
        
        room = self.rooms.get(room_id)
        if not room:
            return None, "房间不存在"
        
        if spectate:
            player.color = None
            player.role = "spectator"
            room.spectators.append(player)
        else:
            if room.players.get("guest") is not None:
                return None, "房间已满"
            
            player.color = StoneColor.WHITE
            player.timeRemaining = 20 * 60 * 1000
            player.byoyomiCount = 3
            player.isInByoyomi = False
            room.players["guest"] = player
        
        return room, None

    def get_room_by_password(self, password: str) -> Optional[Room]:
        room_id = self.password_map.get(password.upper())
        if room_id:
            return self.rooms.get(room_id)
        return None

    def get_room_by_player(self, player_id: str) -> Optional[Room]:
        for room in self.rooms.values():
            host = room.players.get("host")
            guest = room.players.get("guest")
            if host and host.id == player_id:
                return room
            if guest and guest.id == player_id:
                return room
            for spectator in room.spectators:
                if spectator.id == player_id:
                    return room
        return None

    def player_ready(self, password: str, player_id: str) -> bool:
        room = self.get_room_by_password(password)
        if not room:
            return False

        host = room.players.get("host")
        guest = room.players.get("guest")
        
        if host and host.id == player_id:
            host.isReady = True
        elif guest and guest.id == player_id:
            guest.isReady = True

        if host and guest:
            return host.isReady and guest.isReady
        return False

    def start_game(self, password: str) -> Optional[Room]:
        room = self.get_room_by_password(password)
        if not room:
            return None

        room.status = RoomStatus.PLAYING
        room.startedAt = int(uuid.time.time() * 1000)
        room.currentTurn = StoneColor.BLACK
        
        host = room.players.get("host")
        guest = room.players.get("guest")
        
        if host:
            host.timeRemaining = 20 * 60 * 1000
            host.byoyomiCount = 3
            host.isInByoyomi = False
        if guest:
            guest.timeRemaining = 20 * 60 * 1000
            guest.byoyomiCount = 3
            guest.isInByoyomi = False

        return room

    def make_move(self, password: str, player_id: str, x: int, y: int) -> tuple[Optional[Move], Optional[str]]:
        room = self.get_room_by_password(password)
        if not room:
            return None, "房间不存在"

        if room.status != RoomStatus.PLAYING:
            return None, "游戏未开始"

        host = room.players.get("host")
        guest = room.players.get("guest")
        
        player = None
        if host and host.id == player_id:
            player = host
        elif guest and guest.id == player_id:
            player = guest
        
        if not player:
            return None, "非游戏参与者"
        
        if player.color != room.currentTurn:
            return None, "不是你的回合"

        color = player.color
        
        is_valid, error = validate_move(room.board, x, y, color, room.koPosition)
        if not is_valid:
            return None, error

        captured = make_move(room.board, x, y, color)
        
        ko_pos = None
        if len(captured) == 1:
            ko_pos = Position(x=x, y=y)
        
        move = Move(
            position=Position(x=x, y=y),
            color=color,
            moveNumber=len(room.moves) + 1,
            timestamp=int(uuid.time.time() * 1000),
            capturedStones=captured
        )
        
        room.moves.append(move)
        room.lastMove = move
        room.koPosition = ko_pos
        
        room.currentTurn = StoneColor.BLACK if color == StoneColor.WHITE else StoneColor.WHITE

        return move, None

    def pass_turn(self, password: str, player_id: str) -> tuple[Optional[Move], Optional[str]]:
        room = self.get_room_by_password(password)
        if not room:
            return None, "房间不存在"

        if room.status != RoomStatus.PLAYING:
            return None, "游戏未开始"

        host = room.players.get("host")
        guest = room.players.get("guest")
        
        player = None
        if host and host.id == player_id:
            player = host
        elif guest and guest.id == player_id:
            player = guest
        
        if not player:
            return None, "非游戏参与者"

        color = player.color
        move = Move(
            position=Position(x=-1, y=-1),
            color=color,
            moveNumber=len(room.moves) + 1,
            timestamp=int(uuid.time.time() * 1000),
            capturedStones=[]
        )
        
        room.moves.append(move)
        room.lastMove = None
        room.koPosition = None
        
        room.currentTurn = StoneColor.BLACK if color == StoneColor.WHITE else StoneColor.WHITE
        
        if len(room.moves) >= 2:
            last_two = room.moves[-2:]
            if (last_two[0].position.x == -1 and last_two[1].position.x == -1):
                self._end_game(room)
                return move, None

        return move, None

    def resign(self, password: str, player_id: str) -> tuple[Optional[StoneColor], Optional[str]]:
        room = self.get_room_by_password(password)
        if not room:
            return None, "房间不存在"

        if room.status != RoomStatus.PLAYING:
            return None, "游戏未开始"

        host = room.players.get("host")
        guest = room.players.get("guest")
        
        winner = None
        if host and host.id == player_id:
            winner = StoneColor.WHITE if guest else StoneColor.BLACK
        elif guest and guest.id == player_id:
            winner = StoneColor.BLACK

        if winner:
            room.status = RoomStatus.FINISHED
            room.winner = winner
            room.result = "对方认输"
            return winner, None

        return None, "非游戏参与者"

    def leave_room(self, password: str, player_id: str) -> bool:
        room = self.get_room_by_password(password)
        if not room:
            return False

        host = room.players.get("host")
        guest = room.players.get("guest")
        
        if host and host.id == player_id:
            room.players["host"] = None
        elif guest and guest.id == player_id:
            room.players["guest"] = None
        else:
            room.spectators = [s for s in room.spectators if s.id != player_id]

        if room.players.get("host") is None and room.players.get("guest") is None:
            del self.rooms[room.id]
            del self.password_map[password]
            return True
        else:
            room.status = RoomStatus.WAITING
            room.board = create_empty_board()
            room.moves = []
            room.currentTurn = StoneColor.BLACK
            room.koPosition = None
            room.lastMove = None
            return False

    def set_player_connected(self, password: str, player_id: str, connected: bool):
        room = self.get_room_by_password(password)
        if not room:
            return

        host = room.players.get("host")
        guest = room.players.get("guest")
        
        if host and host.id == player_id:
            host.connected = connected
        elif guest and guest.id == player_id:
            guest.connected = connected

    def _end_game(self, room: Room):
        room.status = RoomStatus.FINISHED
        score = calculate_score(room.board)
        winner = score["winner"]
        room.winner = winner
        
        if winner == "draw":
            room.result = f"和棋 (黑:{score['black']} vs 白:{score['white']})"
        else:
            room.result = f"{'黑' if winner == StoneColor.BLACK else '白'}胜 (黑:{score['black']} vs 白:{score['white']})"

    def _generate_password(self) -> str:
        import random
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        while True:
            password = "".join(random.choice(chars) for _ in range(5))
            if password not in self.password_map:
                return password


room_manager = RoomManager()