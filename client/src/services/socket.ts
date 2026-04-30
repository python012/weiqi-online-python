// WebSocket 客户端服务层
import { Room, Player, ChatMessage, Position } from '../types';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

class SocketService {
  private ws: WebSocket | null = null;
  private sid: string = '';
  private listeners: Map<string, Set<Function>> = new Map();
  private pendingMessages: Array<{ event: string; data: any }> = [];

  /**
   * 生成唯一客户端 ID
   */
  private generateSid(): string {
    return 'client_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
  }

  /**
   * 连接 WebSocket 服务器
   */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    this.sid = this.generateSid();
    this.ws = new WebSocket(`${WS_URL}/ws/${this.sid}`);

    this.ws.onopen = () => {
      console.log('[WS] Connected, sid:', this.sid);
      // 发送等待的消息
      this.pendingMessages.forEach(msg => {
        this.ws?.send(JSON.stringify(msg));
      });
      this.pendingMessages = [];
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const handlers = this.listeners.get(msg.event);
        if (handlers) {
          handlers.forEach(h => h(msg.data));
        }
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    this.ws.onclose = () => {
      console.log('[WS] Disconnected');
      // 3秒后重连
      setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = (err) => {
      console.error('[WS] Error:', err);
    };
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * 是否已连接
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * 发送消息
   */
  private send(event: string, data?: any): void {
    const msg = { event, data };
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    } else {
      this.pendingMessages.push(msg);
    }
  }

  /**
   * 创建房间
   */
  createRoom(roomName: string): void {
    this.send('room:create', roomName);
  }

  /**
   * 加入房间
   */
  joinRoom(password: string): void {
    this.send('room:join', password);
  }

  /**
   * 离开房间
   */
  leaveRoom(): void {
    this.send('room:leave');
  }

  /**
   * 落子
   */
  makeMove(position: Position): void {
    this.send('game:move', position);
  }

  /**
   * Pass
   */
  pass(): void {
    this.send('game:pass');
  }

  /**
   * 认输
   */
  resign(): void {
    this.send('game:resign');
  }

  /**
   * 确认准备
   */
  setReady(): void {
    this.send('room:ready');
  }

  /**
   * 发送聊天消息
   */
  sendChatMessage(content: string): void {
    this.send('chat:send', content);
  }

  // 事件监听方法
  onRoomCreated(callback: (room: Room) => void): void { this.on('room:created', callback); }
  onRoomJoined(callback: (room: Room, player: Player) => void): void { this.on('room:joined', callback); }
  onRoomUpdated(callback: (room: Room) => void): void { this.on('room:updated', callback); }
  onPlayerJoined(callback: (player: Player) => void): void { this.on('room:player-joined', callback); }
  onPlayerLeft(callback: (playerId: string) => void): void { this.on('room:player-left', callback); }
  onGameStart(callback: (room: Room) => void): void { this.on('room:game-start', callback); }
  onMove(callback: (data: { move: any; room: Room }) => void): void { this.on('game:move', callback); }
  onPass(callback: (data: { move: any; room: Room }) => void): void { this.on('game:pass', callback); }
  onResign(callback: (winner: 'black' | 'white') => void): void { this.on('game:resign', callback); }
  onGameEnd(callback: (room: Room) => void): void { this.on('game:end', callback); }
  onChatMessage(callback: (message: ChatMessage) => void): void { this.on('chat:message', callback); }
  onError(callback: (error: string) => void): void { this.on('error', callback); }

  private on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  // 移除监听
  offRoomCreated(callback: (room: Room) => void): void { this.off('room:created', callback); }
  offRoomJoined(callback: (room: Room, player: Player) => void): void { this.off('room:joined', callback); }
  offRoomUpdated(callback: (room: Room) => void): void { this.off('room:updated', callback); }
  offPlayerJoined(callback: (player: Player) => void): void { this.off('room:player-joined', callback); }
  offPlayerLeft(callback: (playerId: string) => void): void { this.off('room:player-left', callback); }
  offGameStart(callback: (room: Room) => void): void { this.off('room:game-start', callback); }
  offMove(callback: (data: { move: any; room: Room }) => void): void { this.off('game:move', callback); }
  offPass(callback: (data: { move: any; room: Room }) => void): void { this.off('game:pass', callback); }
  offResign(callback: (winner: 'black' | 'white') => void): void { this.off('game:resign', callback); }
  offGameEnd(callback: (room: Room) => void): void { this.off('game:end', callback); }
  offChatMessage(callback: (message: ChatMessage) => void): void { this.off('chat:message', callback); }
  offError(callback: (error: string) => void): void { this.off('error', callback); }

  private off(event: string, callback: Function): void {
    this.listeners.get(event)?.delete(callback);
  }
}

// 导出单例
export const socketService = new SocketService();
