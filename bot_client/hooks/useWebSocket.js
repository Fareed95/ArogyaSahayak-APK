// lib/websocket.js
export class ChatWebSocket {
    constructor(url) {
      this.url = url;
      this.socket = null;
      this.messageHandlers = new Map();
      this.reconnectAttempts = 0;
      this.maxReconnectAttempts = 5;
    }
  
    connect() {
      return new Promise((resolve, reject) => {
        this.socket = new WebSocket(this.url);
        
        this.socket.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };
  
        this.socket.onmessage = (event) => {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        };
  
        this.socket.onclose = () => {
          console.log('WebSocket disconnected');
          this.attemptReconnect();
        };
  
        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      });
    }
  
    attemptReconnect() {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
      }
    }
  
    on(messageType, handler) {
      this.messageHandlers.set(messageType, handler);
    }
  
    handleMessage(data) {
      const handler = this.messageHandlers.get(data.type);
      if (handler) {
        handler(data);
      }
    }
  
    send(message) {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify(message));
      } else {
        console.error('WebSocket is not connected');
      }
    }
  
    disconnect() {
      if (this.socket) {
        this.socket.close();
      }
    }
  }