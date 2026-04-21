# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

围棋在线对弈平台 - A real-time Go (Weiqi) game platform with React frontend and Python FastAPI backend. Players can create rooms with passwords to play with friends without registration.

## Commands

### Backend (Python)

```bash
# Install backend dependencies
pip install fastapi uvicorn python-socketio pydantic

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

## Architecture

### Backend (`backend/`)

FastAPI + Socket.IO hybrid architecture:

- **main.py**: FastAPI app entry point with Socket.IO server. Handles WebSocket events for room management, game moves, and chat. Uses `socket_map` to track sid→password→player_id mappings.
- **room_manager.py**: `RoomManager` class managing all game rooms in-memory. Creates rooms, handles joining/leaving, validates moves, manages game state transitions (WAITING → PLAYING → FINISHED).
- **game_engine.py**: Go rule implementation including position validation, liberty calculation (`get_liberties`), capture logic (`capture_stones`), ko rule enforcement, and territory scoring (`calculate_score` using Chinese rules with 3.75 komi).
- **types.py**: Pydantic models for `Room`, `Player`, `Move`, `StoneColor`, `Position`, `ChatMessage`. Game config constants (19x19 board, 20min base time + 3x60s byoyomi).

### Frontend (`client/src/`)

React + TypeScript + Vite with Socket.IO client:

- **services/socket.ts**: Singleton `socketService` wrapping Socket.IO client. Methods for game events (create/join room, move, pass, resign, chat) and event listeners.
- **pages/**: Home (create/join room), WaitingRoom (await game start), Game (active play), Review (game replay with move navigation).
- **components/**: Board (19x19 grid with hover preview, star points, move numbers), Chat (messages with system/user distinction), Timer (countdown with byoyomi display).
- **game/engine.ts**: Frontend Go rule validation (mirrors backend for immediate feedback).

### Communication Flow

Socket.IO is the primary communication channel. HTTP endpoint `/api/health` is only for health checks.

Key WebSocket events:
- Client → Server: `room:create`, `room:join`, `room:ready`, `game:move`, `game:pass`, `game:resign`, `chat:send`
- Server → Room: `room:created`, `room:updated`, `game:move`, `game:end`, `chat:message`

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
