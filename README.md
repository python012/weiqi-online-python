---
title: 围棋在线对弈
emoji: ⭕
colorFrom: yellow
colorTo: black
sdk: docker
app_port: 7860
pinned: false
license: mit
tags:
  - game
  - go
  - weiqi
  - real-time
---

# 围棋在线对弈平台

一个面向休闲娱乐玩家的围棋在线对弈平台，无需注册即可快速上手，创建房间邀请好友对弈。

## 技术栈

- **前端**: React 18 + TypeScript + Vite
- **后端**: Python FastAPI + 原生 WebSocket
- **实时通信**: 原生 WebSocket
- **部署**: 支持本地运行和 Hugging Face Space

## 项目结构

```
weiqi-online-python/
├── backend/                 # Python 后端
│   ├── main.py            # FastAPI 主入口 + WebSocket + 静态文件服务
│   ├── types.py           # Pydantic 数据模型
│   ├── game_engine.py     # 围棋规则引擎 (禁着、提子、打劫、终局计算)
│   └── room_manager.py    # 房间状态管理
├── client/                 # React 前端
│   └── src/
│       ├── pages/         # Home, Game, Review, WaitingRoom
│       ├── components/    # Board, Timer, Chat
│       ├── game/           # 前端围棋规则校验
│       └── services/      # WebSocket 客户端
├── Dockerfile             # HF Spaces Docker 构建 (前端+后端)
├── requirements.txt       # Python 依赖
└── app.py                 # 本地入口
```

## 快速开始

### 后端 (端口 4000)

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 4000
```

### 前端 (端口 3000)

```bash
cd client
npm install
npm run dev
```

访问 http://localhost:3000

## 游戏规则

- **棋盘**: 19×19
- **执子**: 黑先白后，交替落子
- **禁着**: 自杀(无气)、立即打劫
- **提子**: 围住对方棋子使其无气即被提掉
- **终局**: 双方连续 Pass 或认输
- **计时**: 20 分钟基础 + 3 次 60 秒读秒
- **胜负**: 中国规则，黑贴 3.75 目

## 房间机制

- 房间密码: 5 位大写字母数字 (A-Z, 2-9，排除易混淆字符)
- 每房间固定 2 人: 房主执黑，访客执白
- 无注册，连接后自动分配随机昵称 (形容词+动物名)
- 房间状态存储于内存，重启后房间消失

## 通信协议

**WebSocket 是唯一通信渠道**，HTTP 仅用于健康检查。

### 客户端 → 服务端

| 事件 | 说明 |
|------|------|
| `room:create` | 创建房间 |
| `room:join` | 加入房间 |
| `room:leave` | 离开房间 |
| `game:move` | 落子 |
| `game:pass` | 停一手 |
| `game:resign` | 认输 |
| `chat:send` | 发送消息 |

### 服务端 → 房间

| 事件 | 说明 |
|------|------|
| `room:created` | 房间创建成功 |
| `room:game-start` | 游戏开始 |
| `room:player-left` | 玩家离开 |
| `game:move` | 落子广播 |
| `game:pass` | 停手广播 |
| `game:resign` | 认输 |
| `game:end` | 游戏结束 |
| `chat:message` | 聊天消息 |

## 页面说明

- **Home**: 创建/加入房间
- **WaitingRoom**: 等待对手连接
- **Game**: 对弈界面 (棋盘、计时器、聊天)
- **Review**: 棋谱复盘

## Hugging Face 部署

通过 Docker 自动构建部署。创建 HF Space 时选择 **Docker** SDK，关联此仓库即可。

构建流程：`Dockerfile` 先编译 React 前端到 `static/`，再由 FastAPI 同时提供 API 和前端静态文件。

## 测试

```bash
pytest              # 后端测试
cd client && npm run lint   # 前端 ESLint
```