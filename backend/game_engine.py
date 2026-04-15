# 围棋规则引擎 - Python 版本
from typing import Optional
from pydantic import BaseModel
from enum import Enum


class StoneColor(str, Enum):
    BLACK = "black"
    WHITE = "white"


class Position(BaseModel):
    x: int
    y: int


class Move(BaseModel):
    position: Position
    color: StoneColor
    move_number: int
    timestamp: int
    captured_stones: list[Position] = []


BOARD_SIZE = 19

BASE_TIME = 20 * 60 * 1000
BYOYOMI_TIME = 60 * 1000
BYOYOMI_COUNT = 3


def is_valid_position(x: int, y: int) -> bool:
    return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE


def get_connected_group(
    board: list[list[Optional[StoneColor]]],
    x: int,
    y: int,
    color: StoneColor,
    visited: list[list[bool]]
) -> list[Position]:
    if not is_valid_position(x, y):
        return []
    if board[y][x] != color:
        return []
    if visited[y][x]:
        return []

    visited[y][x] = True
    group: list[Position] = [Position(x=x, y=y)]

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    for dx, dy in directions:
        group.extend(get_connected_group(board, x + dx, y + dy, color, visited))

    return group


def get_liberties(
    board: list[list[Optional[StoneColor]]],
    x: int,
    y: int
) -> int:
    color = board[y][x]
    if color is None:
        return 0

    visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    group = get_connected_group(board, x, y, color, visited)

    liberties = set()
    for pos in group:
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = pos.x + dx, pos.y + dy
            if is_valid_position(nx, ny) and board[ny][nx] is None:
                liberties.add(f"{nx},{ny}")

    return len(liberties)


def capture_stones(
    board: list[list[Optional[StoneColor]]],
    x: int,
    y: int,
    color: StoneColor
) -> list[Position]:
    opponent_color = StoneColor.BLACK if color == StoneColor.WHITE else StoneColor.WHITE
    captured_stones: list[Position] = []

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if is_valid_position(nx, ny) and board[ny][nx] == opponent_color:
            liberties = get_liberties(board, nx, ny)
            if liberties == 0:
                visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
                group = get_connected_group(board, nx, ny, opponent_color, visited)
                for pos in group:
                    if not any(s.x == pos.x and s.y == pos.y for s in captured_stones):
                        captured_stones.append(pos)

    for pos in captured_stones:
        board[pos.y][pos.x] = None

    return captured_stones


def validate_move(
    board: list[list[Optional[StoneColor]]],
    x: int,
    y: int,
    color: StoneColor,
    ko_position: Optional[Position] = None
) -> tuple[bool, Optional[str]]:
    if not is_valid_position(x, y):
        return False, "无效的位置"

    if board[y][x] is not None:
        return False, "该位置已有棋子"

    if ko_position and ko_position.x == x and ko_position.y == y:
        return False, "打劫规则：不能立即回提"

    test_board = [row[:] for row in board]
    test_board[y][x] = color
    captured = capture_stones(test_board, x, y, color)

    if len(captured) == 0:
        liberties = get_liberties(test_board, x, y)
        if liberties == 0:
            return False, "禁止自杀：该位置无气"

    return True, None


def make_move(
    board: list[list[Optional[StoneColor]]],
    x: int,
    y: int,
    color: StoneColor
) -> list[Position]:
    board[y][x] = color
    captured = capture_stones(board, x, y, color)
    return captured


def create_empty_board(size: int = 19) -> list[list[Optional[StoneColor]]]:
    return [[None] * size for _ in range(size)]


def calculate_score(board: list[list[Optional[StoneColor]]]) -> dict:
    territory = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] is not None:
                territory[y][x] = board[y][x]

    visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]

    def flood_fill(x: int, y: int, color: Optional[str]):
        if not is_valid_position(x, y):
            return
        if visited[y][x]:
            return
        if territory[y][x] is not None:
            return

        visited[y][x] = True
        territory[y][x] = color  # type: ignore

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = x + dx, y + dy
            if is_valid_position(nx, ny):
                if board[ny][nx] is None:
                    flood_fill(nx, ny, color)
                elif board[ny][nx] != color and territory[ny][nx] is None:
                    flood_fill(nx, ny, "dame")

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] is None and not visited[y][x]:
                flood_fill(x, y, "dame")

    black_territory = 0
    white_territory = 0
    black_stones = 0
    white_stones = 0

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if territory[y][x] == StoneColor.BLACK:
                black_territory += 1
            elif territory[y][x] == StoneColor.WHITE:
                white_territory += 1

            if board[y][x] == StoneColor.BLACK:
                black_stones += 1
            elif board[y][x] == StoneColor.WHITE:
                white_stones += 1

    komi = 3.75
    black_total = black_stones + black_territory
    white_total = white_stones + white_territory + komi

    if black_total > white_total:
        winner = StoneColor.BLACK
    elif white_total > black_total:
        winner = StoneColor.WHITE
    else:
        winner = "draw"

    return {
        "black": black_total,
        "white": white_total,
        "winner": winner
    }