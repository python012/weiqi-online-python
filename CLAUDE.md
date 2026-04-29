# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

围棋在线对弈平台 - A real-time Go (Weiqi) game platform with React frontend and Python FastAPI backend. Players can create rooms with passwords to play with friends without registration.

## Commands

### Backend (Python)

```bash
# Install backend dependencies
pip install -r requirements.txt  # fastapi, uvicorn, pydantic

# Start backend server (default port 4000)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 4000

# Run tests
pytest

# Run linting
ruff check
```

### Frontend (React/TypeScript)

```bash
cd client
npm install
npm run dev      # Start dev server (port 3000)
npm run build    # Build for production
npm run lint     # ESLint check
```

### HuggingFace Space Deployment

```bash
# HF Space entry point (port 7860)
python app.py
# or
uvicorn app:app --host 0.0.0.0 --port 7860
```

## Architecture

### Backend (`backend/`)

FastAPI with native WebSocket (NOT python-socketio):

- **main.py**: FastAPI app with WebSocket endpoint `/ws/{sid}`. Uses `ConnectionManager` class to manage active connections (`sid → websocket`) and player mappings (`sid → {password, player_id}`). Handles all WebSocket events.
- **room_manager.py**: `RoomManager` class managing all game rooms in-memory. Creates rooms, handles joining/leaving, validates moves, manages game state transitions (WAITING → PLAYING → FINISHED).
- **game_engine.py**: Go rule implementation including position validation, liberty calculation (`get_liberties`), capture logic (`capture_stones`), ko rule enforcement, and territory scoring (`calculate_score` using Chinese rules with 3.75 komi).
- **types.py**: Pydantic models for `Room`, `Player`, `Move`, `StoneColor`, `Position`, `ChatMessage`. Game config constants (19x19 board, 20min base time + 3x60s byoyomi).
- **hf_space.py**: HF Space-specific wrapper (currently just re-exports `backend.main:app`).

### Root Files

- **app.py**: HuggingFace Space entry point - imports and exposes `backend.main:app`
- **hf_space.json**: Space metadata (title, emoji, SDK, tags)

### Frontend (`client/src/`)

React + TypeScript + Vite with native WebSocket client:

- **services/socket.ts**: Singleton `socketService` wrapping native WebSocket. Connects to `ws://host:port/ws/{sid}`. Methods for game events (create/join room, move, pass, resign, chat) and event listeners.
- **pages/**: Home (create/join room), WaitingRoom (await game start), Game (active play), Review (game replay with move navigation).
- **components/**: Board (19x19 grid with hover preview, star points, move numbers), Chat (messages with system/user distinction), Timer (countdown with byoyomi display).
- **game/engine.ts**: Frontend Go rule validation (mirrors backend for immediate feedback).

### Communication Flow

Native WebSocket is the primary communication channel. HTTP endpoint `/api/health` is only for health checks.

WebSocket endpoint: `ws://{host}:{port}/ws/{sid}` where `sid` is a unique session identifier.

Key WebSocket events (JSON messages with `{event: string, data: any}`):

**Client → Server:**
- `room:create` - Create new room (data: room_name)
- `room:join` - Join existing room (data: password)
- `room:leave` - Leave current room
- `game:move` - Place stone (data: {x, y})
- `game:pass` - Pass turn
- `game:resign` - Resign game
- `chat:send` - Send message (data: content)

**Server → Room:**
- `room:created` - Room created successfully
- `room:game-start` - Both players connected, game begins
- `room:player-left` - Player disconnected
- `room:updated` - Room state changed
- `game:move` - Stone placed with updated board state
- `game:pass` - Turn passed
- `game:resign` - Player resigned
- `game:end` - Game finished (with final state and scores)
- `chat:message` - New chat message
- `error` - Error response with message

Room passwords are 5-character uppercase strings (A-Z, 2-9, excluding confusing chars). Room data is stored in-memory; restart clears all rooms.

### Game Rules

- 19x19 board, black moves first
- Forbidden: suicide (no liberties), immediate ko recapture
- Scoring: Chinese territory counting, 3.75 komi for white
- Timer: 20 minutes + 3 × 60 second byoyomi

## Development Notes

- No auth required - players get random nicknames (adjective + animal) on connection
- Each room has exactly 2 players (host/black, guest/white)
- Frontend and backend share similar type definitions (`types.ts` vs `types.py`)
- Room lifecycle: created (host joins) → waiting (guest joins) → playing (both ready) → finished
