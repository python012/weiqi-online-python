# 后端技术文档

## 目录

1. [架构概述](#架构概述)
2. [模块结构](#模块结构)
3. [核心类型定义](#核心类型定义)
4. [围棋规则引擎](#围棋规则引擎)
5. [房间管理器](#房间管理器)
6. [Socket.IO 事件处理](#socketio-事件处理)
7. [API 参考](#api-参考)

---

## 架构概述

后端采用 **FastAPI + Socket.IO** 的混合架构：

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI App                         │
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │   HTTP Server   │    │   Socket.IO Server (ASGI)  │ │
│  │  /api/health    │◄──►│   Real-time Game Events    │ │
│  └─────────────────┘    └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

- **FastAPI**: 提供 HTTP REST 接口（如健康检查）
- **Socket.IO**: 处理实时双向通信（游戏逻辑、聊天）
- **In-Memory 存储**: 房间和游戏状态存储在内存中

### 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.109+ | Web 框架 |
| python-socketio | 5.11+ | WebSocket 通信 |
| Pydantic | 2.5+ | 数据验证与序列化 |
| Uvicorn | 0.27+ | ASGI 服务器 |

---

## 模块结构

```
backend/
├── __init__.py      # 包初始化
├── main.py          # 应用入口 (FastAPI + Socket.IO)
├── types.py         # Pydantic 数据模型
├── game_engine.py   # 围棋规则引擎
└── room_manager.py  # 房间状态管理
```

---

## 核心类型定义

位于 `types.py`，使用 Pydantic 定义所有数据模型。

### 枚举类型

```python
class StoneColor(str, Enum):
    BLACK = "black"
    WHITE = "white"

class PlayerRole(str, Enum):
    HOST = "host"       # 房主
    GUEST = "guest"    # 加入者
    SPECTATOR = "spectator"  # 观战者

class RoomStatus(str, Enum):
    WAITING = "waiting"   # 等待对手
    PLAYING = "playing"   # 对局中
    FINISHED = "finished" # 已结束
```

### 数据模型

#### Position - 棋盘位置
```python
class Position(BaseModel):
    x: int  # 0-18
    y: int  # 0-18
```

#### Move - 一步棋
```python
class Move(BaseModel):
    position: Position          # 落子位置
    color: StoneColor           # 棋子颜色
    moveNumber: int             # 序号 (1, 2, 3...)
    timestamp: int              # 时间戳 (毫秒)
    capturedStones: list[Position]  # 被提掉的棋子
```

#### Player - 玩家
```python
class Player(BaseModel):
    id: str                     # 唯一标识
    nickname: str               # 随机生成的昵称
    role: PlayerRole            # 角色
    color: Optional[StoneColor] # 执子颜色 (null=观战)
    isReady: bool              # 是否确认开始
    connected: bool             # 在线状态
    timeRemaining: int         # 剩余时间 (毫秒)
    byoyomiCount: int          # 读秒次数
    isInByoyomi: bool          # 是否进入读秒
```

#### Room - 房间
```python
class Room(BaseModel):
    id: str                          # 房间 ID (UUID)
    name: str                       # 房间名称
    password: str                   # 房间密码 (5位)
    status: RoomStatus              # 房间状态
    players: dict                   # {"host": Player, "guest": Player}
    spectators: list[Player]         # 观战者列表
    board: list[list[Optional[StoneColor]]]  # 19x19 棋盘
    moves: list[Move]               # 棋谱
    currentTurn: StoneColor         # 当前执子方
    koPosition: Optional[Position] # 打劫位置
    lastMove: Optional[Move]       # 最后一步
    winner: Optional[StoneColor]   # 胜者
    result: str                     # 对局结果描述
    startedAt: Optional[int]       # 开始时间戳
```

#### ChatMessage - 聊天消息
```python
class ChatMessage(BaseModel):
    id: str              # 消息 ID
    senderId: str        # 发送者 ID
    senderNickname: str  # 发送者昵称
    content: str         # 消息内容
    timestamp: int       # 时间戳
```

### 游戏配置

```python
GAME_CONFIG = {
    "BOARD_SIZE": 19,           # 19路棋盘
    "BASE_TIME": 20 * 60 * 1000,  # 20分钟
    "BYOYOMI_TIME": 60 * 1000,    # 60秒读秒
    "BYOYOMI_COUNT": 3,           # 3次读秒
}
```

---

## 围棋规则引擎

位于 `game_engine.py`，实现完整的中国围棋规则。

### 核心函数

#### 1. 位置验证
```python
def is_valid_position(x: int, y: int) -> bool
```
检查坐标是否在 0-18 范围内。

#### 2. 获取连通块
```python
def get_connected_group(
    board, x, y, color, visited
) -> list[Position]
```
使用深度优先搜索 (DFS) 获取与指定棋子相连的所有同色棋子。

#### 3. 计算气数
```python
def get_liberties(board, x, y) -> int
```
计算棋子或棋子块的气数（周围空位的数量）。

#### 4. 提子
```python
def capture_stones(board, x, y, color) -> list[Position]
```
检查并执行提子，返回被提掉的棋子位置列表。

**算法流程：**
1. 检查落子位置四个方向的对方棋子
2. 计算每个对方棋子块的气数
3. 如果气数为 0，标记为需要提掉
4. 递归获取整个连通块
5. 从棋盘上移除这些棋子

#### 5. 验证落子
```python
def validate_move(
    board, x, y, color, ko_position
) -> tuple[bool, Optional[str]]
```

检查落子是否合法，返回 `(是否有效, 错误信息)`。

**检查规则：**
1. 位置有效性
2. 目标位置为空
3. 打劫规则（不能立即回提）
4. 自杀规则（不能无气落子）

#### 6. 执行落子
```python
def make_move(board, x, y, color) -> list[Position]
```
在棋盘上落子并返回被提掉的棋子。

#### 7. 计算胜负
```python
def calculate_score(board) -> dict
```

使用中国规则数子法计算胜负。

**算法流程：**
1. 标记所有棋子
2. 对空位进行泛洪填充 (Flood Fill)
3. 统计各方领地 + 棋子数
4. 黑方贴 3.75 子
5. 比较后得出胜者

---

## 房间管理器

位于 `room_manager.py`，管理所有游戏房间和游戏状态。

### RoomManager 类

```python
class RoomManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}        # room_id -> Room
        self.password_map: dict[str, str] = {}   # password -> room_id
```

#### 主要方法

| 方法 | 说明 |
|------|------|
| `create_room(name, host)` | 创建新房间 |
| `join_room(password, player)` | 加入房间 |
| `get_room_by_password(password)` | 通过密码获取房间 |
| `player_ready(password, player_id)` | 玩家确认准备 |
| `start_game(password)` | 开始游戏 |
| `make_move(password, player_id, x, y)` | 执行落子 |
| `pass_turn(password, player_id)` | 停一手 |
| `resign(password, player_id)` | 认输 |
| `leave_room(password, player_id)` | 离开房间 |

### 房间生命周期

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  WAITING   │────►│  PLAYING    │────►│  FINISHED   │
│  等待中     │     │  对局中     │     │  已结束     │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      │ 双方准备就绪       │ 棋局结束          │
      ▼                   ▼                   ▼
   开始游戏           认输/终局             清理
```

### 密码生成

```python
def _generate_password(self) -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 避免易混淆字符
    password = "".join(random.choice(chars) for _ in range(5))
```

---

## Socket.IO 事件处理

位于 `main.py`，处理所有 WebSocket 事件。

### 事件映射

| 客户端事件 | 服务器处理 | 说明 |
|------------|-------------|------|
| `room_create` | `room_create(sid, room_name)` | 创建房间 |
| `room_join` | `room_join(sid, password)` | 加入房间 |
| `room_ready` | `room_ready(sid)` | 确认准备 |
| `room_leave` | `room_leave(sid)` | 离开房间 |
| `game_move` | `game_move(sid, position)` | 落子 |
| `game_pass` | `game_pass(sid)` | 停一手 |
| `game_resign` | `game_resign(sid)` | 认输 |
| `chat_send` | `chat_send(sid, content)` | 发送消息 |

### 服务器推送事件

| 事件 | 数据 | 说明 |
|------|------|------|
| `room:created` | Room | 房间创建成功 |
| `room:joined` | Room, Player | 加入房间成功 |
| `room:updated` | Room | 房间状态更新 |
| `room:player-joined` | Player | 新玩家加入 |
| `room:player-left` | playerId | 玩家离开 |
| `room:game-start` | Room | 游戏开始 |
| `game:move` | Move, Room | 落子事件 |
| `game:pass` | Move, Room | 停一手 |
| `game:resign` | StoneColor | 认输 |
| `game:end` | Room | 游戏结束 |
| `chat:message` | ChatMessage | 聊天消息 |
| `error` | string | 错误信息 |

### Socket 映射

```python
socket_map: dict[str, dict] = {
    "socket_id": {
        "password": "ABC12",    # 所在房间密码
        "player_id": "xxx"      # 玩家 ID
    }
}
```

用于在事件处理时关联 Socket ID 和玩家信息。

### 事件处理流程示例

#### 创建房间
```
客户端                           服务器
   │                               │
   │──── room:create (roomName) ──►│
   │                               │ 1. 生成 player_id
   │                               │ 2. 创建 Player
   │                               │ 3. 创建 Room
   │                               │ 4. 关联 socket_map
   │◄─── room:created (Room) ─────│
   │                               │
```

#### 落子流程
```
客户端                           服务器
   │                               │
   │──── game:move ({x, y}) ─────►│
   │                               │ 1. 验证玩家身份
   │                               │ 2. 验证落子规则
   │                               │ 3. 执行落子
   │                               │ 4. 更新棋盘
   │                               │ 5. 切换执子方
   │◄─── game:move (Move, Room) ───│
   │                               │
```

---

## API 参考

### HTTP 接口

#### 健康检查

```
GET /api/health
```

响应：
```json
{
  "status": "ok",
  "timestamp": 1700000000000
}
```

### Socket.IO 命名空间

使用默认命名空间 `/`，连接 URL: `http://localhost:4000`

---

## 错误处理

### 错误消息

| 错误码 | 消息 | 说明 |
|--------|------|------|
| 1 | 房间不存在 | 密码错误或房间已关闭 |
| 2 | 房间已满 | 已有两名玩家 |
| 3 | 游戏未开始 | 房间状态不是 playing |
| 4 | 非游戏参与者 | 观战者尝试落子 |
| 5 | 不是你的回合 | 轮到对方落子 |
| 6 | 无效的位置 | 坐标超出范围 |
| 7 | 该位置已有棋子 | 已有棋子 |
| 8 | 打劫规则：不能立即回提 | 违反打劫规则 |
| 9 | 禁止自杀：该位置无气 | 违反禁入点规则 |

---

## 性能考虑

1. **内存存储**: 所有房间数据存储在内存中，重启后丢失
2. **密码唯一性**: 密码生成时检查冲突
3. **Pydantic 模型**: 使用 `model_dump()` 转换为字典，减少复制开销
4. **房间清理**: 双方都离开时删除房间数据

---

## 扩展建议

1. **持久化存储**: 接入 Redis 或数据库存储房间状态
2. **房间超时**: 添加房间自动清理机制
3. **复盘功能**: 保存棋谱到数据库支持回放
4. **多房间观战**: 支持观战多个房间
5. **用户认证**: 添加登录/注册功能