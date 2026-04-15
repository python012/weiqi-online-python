# 围棋在线对弈平台 (Python 版)

一个面向休闲娱乐玩家的围棋在线对弈平台，无需注册即可快速上手，创建房间邀请好友对弈。

## 技术栈

- **前端**: React + TypeScript + Vite
- **后端**: Python FastAPI + Socket.IO
- **实时通信**: WebSocket

## 项目结构

```
weiqi-online-python-v2/
├── backend/          # Python FastAPI 后端
│   ├── main.py       # 主入口 (Uvicorn + Socket.IO)
│   ├── types.py      # Pydantic 类型定义
│   ├── game_engine.py # 围棋规则引擎
│   └── room_manager.py # 房间状态管理
├── client/           # React 前端 (复用原项目)
└── pyproject.toml    # Python 依赖配置
```

## 快速开始

### 1. 安装后端依赖

```bash
pip install fastapi uvicorn python-socketio pydantic
```

### 2. 启动后端服务

```bash
cd weiqi-online-python-v2
python -m uvicorn backend.main:app --host 0.0.0.0 --port 4000
```

### 3. 启动前端

```bash
cd client
npm install
npm run dev
```

访问 http://localhost:3000

## 功能特性

- 19×19 标准棋盘
- 完整围棋规则（禁入点、提子、打劫）
- 房间密码邀请对战
- 随机昵称生成（形容词+可爱小动物，如"顽皮的小熊"）
- 实时聊天（支持系统消息、用户消息，带时间戳）
  - 系统消息以 `[系统]` 开头
  - 当前用户消息显示 `[我]`
  - 对方消息显示 `[对方昵称]`
- 对局复盘
- 计时系统（20分钟 + 3次60秒读秒）
- 离开对局确认提示
- 等待房间显示昵称和执棋颜色

## 游戏规则

- 黑先白后，交替落子
- 提子：围住对方棋子使其无气
- 打劫：不能立即回提对方刚提掉的子
- 禁入点：禁止自杀
- 胜负：中国规则数子法，黑贴3.75子

## API 接口

后端同时提供 HTTP REST 和 WebSocket 两种通信方式：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |

WebSocket 事件：

- `room:create` - 创建房间
- `room:join` - 加入房间
- `room:ready` - 确认准备
- `room:leave` - 离开房间
- `game:move` - 落子
- `game:pass` - 停一手
- `game:resign` - 认输
- `chat:send` - 发送消息