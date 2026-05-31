// WebSocket Service - اتصالات في الوقت الفعلي
export interface WebSocketMessage {
  type: 'notification' | 'data_update' | 'system' | 'user_action' | 'transaction' | 'message';
  payload: Record<string, unknown>;
  timestamp: string;
  id: string;
}

export interface NotificationPayload extends Record<string, unknown> {
  title: string;
  body: string;
  type: 'info' | 'success' | 'warning' | 'error';
  data?: Record<string, unknown>;
  persistent?: boolean;
  actions?: Array<{
    label: string;
    action: string;
    style?: 'primary' | 'secondary' | 'danger';
  }>;
}

export interface DataUpdatePayload extends Record<string, unknown> {
  table: string;
  action: 'insert' | 'update' | 'delete';
  data: Record<string, unknown>;
  oldData?: Record<string, unknown>;
}

export interface UserActionPayload extends Record<string, unknown> {
  userId: string;
  action: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface TransactionPayload extends Record<string, unknown> {
  transactionId: string;
  type: 'deposit' | 'withdrawal' | 'transfer';
  amount: number;
  currency: string;
  status: string;
  userId: string;
  details: Record<string, unknown>;
}

export class WebSocketService {
  private static instance: WebSocketService;
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;
  private messageHandlers: Map<string, Array<(message: WebSocketMessage) => void>> = new Map();
  private connectionHandlers: Array<(connected: boolean) => void> = [];
  private pingInterval: NodeJS.Timeout | null = null;
  private messageQueue: WebSocketMessage[] = [];
  private isManualClose = false;

  private constructor() {
    this.url = process.env.REACT_APP_WS_URL || 'wss://api.jadobot.com/ws';
  }

  static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService();
    }
    return WebSocketService.instance;
  }

  // 🔌 الاتصال بـ WebSocket
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      if (this.isConnecting) {
        reject(new Error('Connection already in progress'));
        return;
      }

      this.isConnecting = true;
      this.isManualClose = false;

      try {
        console.log('[WebSocketService] Connecting to:', this.url);
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('[WebSocketService] Connected successfully');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.startPing();
          this.processMessageQueue();
          this.notifyConnectionHandlers(true);
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('[WebSocketService] Error parsing message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('[WebSocketService] Connection closed:', event.code, event.reason);
          this.isConnecting = false;
          this.stopPing();
          this.notifyConnectionHandlers(false);

          if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocketService] WebSocket error:', error);
          this.isConnecting = false;
          reject(error);
        };

      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  // 🔌 قطع الاتصال
  disconnect(): void {
    this.isManualClose = true;
    this.stopPing();
    
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    
    this.messageQueue = [];
    this.messageHandlers.clear();
    this.connectionHandlers = [];
  }

  // 📨 إرسال رسالة
  send(message: Omit<WebSocketMessage, 'timestamp' | 'id'>): void {
    const fullMessage: WebSocketMessage = {
      ...message,
      timestamp: new Date().toISOString(),
      id: this.generateMessageId(),
    };

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(fullMessage));
    } else {
      this.messageQueue.push(fullMessage);
      console.log('[WebSocketService] Message queued (not connected):', fullMessage.type);
    }
  }

  // 📢 إرسال إشعار
  sendNotification(notification: NotificationPayload): void {
    this.send({
      type: 'notification',
      payload: notification,
    });
  }

  // 📊 إرسال تحديث بيانات
  sendDataUpdate(update: DataUpdatePayload): void {
    this.send({
      type: 'data_update',
      payload: update,
    });
  }

  // 👤 إرسال إجراء مستخدم
  sendUserAction(action: UserActionPayload): void {
    this.send({
      type: 'user_action',
      payload: action,
    });
  }

  // 💰 إرسال معاملة
  sendTransaction(transaction: TransactionPayload): void {
    this.send({
      type: 'transaction',
      payload: transaction,
    });
  }

  // 🎯 التسجيل لاستقبال رسائل من نوع معين
  onMessage(type: string, handler: (message: WebSocketMessage) => void): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    
    this.messageHandlers.get(type)!.push(handler);

    // إرجاع دالة لإلغاء التسجيل
    return () => {
      const handlers = this.messageHandlers.get(type);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  // 🔌 التسجيل لتغييرات حالة الاتصال
  onConnectionChange(handler: (connected: boolean) => void): () => void {
    this.connectionHandlers.push(handler);

    // إرجاع دالة لإلغاء التسجيل
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index > -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }

  // 📊 الحصول على حالة الاتصال
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // 🔄 الحصول على حالة الاتصال المفصلة
  getConnectionState(): 'connecting' | 'connected' | 'disconnected' | 'reconnecting' {
    if (this.isConnecting) return 'connecting';
    if (this.isConnected()) return 'connected';
    if (this.reconnectAttempts > 0) return 'reconnecting';
    return 'disconnected';
  }

  // 📈 الحصول على إحصائيات الاتصال
  getConnectionStats(): {
    state: string;
    reconnectAttempts: number;
    queuedMessages: number;
    url: string;
  } {
    return {
      state: this.getConnectionState(),
      reconnectAttempts: this.reconnectAttempts,
      queuedMessages: this.messageQueue.length,
      url: this.url,
    };
  }

  // 🔧 معالجة الرسائل الواردة
  private handleMessage(message: WebSocketMessage): void {
    console.log('[WebSocketService] Received message:', message.type);

    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message);
        } catch (error) {
          console.error('[WebSocketService] Error in message handler:', error);
        }
      });
    }

    // معالجة الرسائل الخاصة
    this.handleSpecialMessages(message);
  }

  // 🔧 معالجة الرسائل الخاصة
  private handleSpecialMessages(message: WebSocketMessage): void {
    switch (message.type) {
      case 'system':
        this.handleSystemMessage(message);
        break;
      case 'notification':
        this.handleNotificationMessage(message);
        break;
    }
  }

  // 🔧 معالجة رسائل النظام
  private handleSystemMessage(message: WebSocketMessage): void {
    const payload = message.payload as { action: string; data?: unknown };
    
    switch (payload.action) {
      case 'ping':
        // الرد على ping
        this.send({
          type: 'system',
          payload: { action: 'pong', timestamp: new Date().toISOString() },
        });
        break;
      case 'pong':
        // تم استلام pong - الاتصال سليم
        console.log('[WebSocketService] Pong received');
        break;
      case 'force_refresh':
        // طلب تحديث强制
        window.location.reload();
        break;
    }
  }

  // 🔔 معالجة رسائل الإشعارات
  private handleNotificationMessage(message: WebSocketMessage): void {
    const notification = message.payload as unknown as NotificationPayload;
    
    // عرض الإشعار في المتصفح إذا كان مدعوماً
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.body,
        icon: '/favicon.ico',
        tag: message.id,
      });
    }

    // إرسال الإشعار إلى التطبيق
    if (notification.persistent) {
      // حفظ الإشعار لعرضه لاحقاً
      this.savePersistentNotification(notification);
    }
  }

  // 💾 حفظ الإشعارات المستمرة
  private savePersistentNotification(notification: NotificationPayload): void {
    try {
      const notifications = JSON.parse(localStorage.getItem('persistent_notifications') || '[]');
      notifications.push({
        ...notification,
        id: this.generateMessageId(),
        timestamp: new Date().toISOString(),
        read: false,
      });
      localStorage.setItem('persistent_notifications', JSON.stringify(notifications));
    } catch (error) {
      console.error('[WebSocketService] Error saving persistent notification:', error);
    }
  }

  // 🔄 جدولة إعادة الاتصال
  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`[WebSocketService] Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    setTimeout(() => {
      if (!this.isManualClose) {
        this.connect().catch(error => {
          console.error('[WebSocketService] Reconnect failed:', error);
        });
      }
    }, delay);
  }

  // 🏓 بدء ping
  private startPing(): void {
    this.stopPing();
    
    this.pingInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send({
          type: 'system',
          payload: { action: 'ping', timestamp: new Date().toISOString() },
        });
      }
    }, 30000); // ping كل 30 ثانية
  }

  // 🛑 إيقاف ping
  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  // 📋 معالجة قائمة انتظار الرسائل
  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift();
      if (message) {
        this.ws?.send(JSON.stringify(message));
      }
    }
  }

  // 📢 إعلام معالجات تغيير الاتصال
  private notifyConnectionHandlers(connected: boolean): void {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(connected);
      } catch (error) {
        console.error('[WebSocketService] Error in connection handler:', error);
      }
    });
  }

  // 🆔 توليد معرف رسالة
  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

export default WebSocketService.getInstance();
