# AGENTS.md

## 快速启动

```bash
# 后端 (端口 4000)
pip install fastapi uvicorn "python-socketio[asyncio]" pydantic
python -m uvicorn backend.main:app --host 0.0.0.0 --port 4000

# 前端 (端口 3000)
cd client && npm install && npm run dev
```

## 项目结构

- `backend/` - Python FastAPI + Socket.IO（主要逻辑）
  - `main.py` - Socket.IO 事件入口，sid→player_id 映射
  - `room_manager.py` - 房间管理，内存存储，重启清空
  - `game_engine.py` - 围棋规则（落子验证、提子、眼算法、终局计算）
  - `types.py` - Pydantic 数据模型
- `client/` - React + TypeScript + Vite（前端 UI）
  - `src/services/socket.ts` - Socket.IO 客户端单例
  - `src/game/engine.ts` - 前端围棋规则校验（与后端 game_engine.py 逻辑一致）

## 通信架构

**Socket.IO 是唯一通信渠道**，HTTP 只有 `/api/health` 健康检查。

关键事件：
- 客户端→服务端：`room:create`、`room:join`、`room:ready`、`game:move`、`game:pass`、`game:resign`、`chat:send`
- 服务端→房间：`room:created`、`room:updated`、`game:move`、`game:end`、`chat:message`

## 游戏规则要点

- 棋盘 19×19，黑先
- 禁着：自杀（无气）、立即打劫
- 终局计法：中国规则，3.75 目贴目
- 计时：20 分钟基础 + 3 次 60 秒读秒

## 房间机制

- 房间密码：5 位大写字母数字（A-Z, 2-9，排除易混淆字符）
- 每个房间固定 2 人（房主执黑，访客执白）
- 无注册，玩家连接后获随机昵称（形容词+动物名）
- 房间状态内存存储，重启后所有房间消失

## 测试

```bash
pytest        # 后端测试
cd client && npm run lint   # 前端 ESLint
```

## HuggingFace 部署

```bash
# 直接在 HF Space 运行
python app.py

# 或使用 uvicorn
uvicorn app:socket_app --host 0.0.0.0 --port 7860
```

关键文件：
- `app.py` - HF Space 入口（端口 7860）
- `hf_space.json` - Space 元数据配置
- `requirements.txt` - Python 依赖
