/**
 * Golike Service - WebSocket Client
 * Connects to LOCAL backend on user's machine
 * (Backend must be running: node server.js)
 */

import { Platform } from '../types';

// Always connect to localhost - backend runs on user's machine
const WS_URL = 'ws://localhost:3001';

type MessageHandler = (data: any) => void;

class GolikeService {
    private ws: WebSocket | null = null;
    private handlers: Map<string, MessageHandler[]> = new Map();
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;

    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(WS_URL);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.emit(data.type, data);
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    reject(error);
                };

                this.ws.onclose = () => {
                    console.log('WebSocket closed');
                    this.tryReconnect();
                };
            } catch (e) {
                reject(e);
            }
        });
    }

    private tryReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connect(), 3000);
        }
    }

    send(action: string, payload: any) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ action, payload }));
        } else {
            console.error('WebSocket not connected');
        }
    }

    on(event: string, handler: MessageHandler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, []);
        }
        this.handlers.get(event)!.push(handler);
    }

    off(event: string, handler: MessageHandler) {
        const handlers = this.handlers.get(event);
        if (handlers) {
            const index = handlers.indexOf(handler);
            if (index > -1) handlers.splice(index, 1);
        }
    }

    private emit(event: string, data: any) {
        const handlers = this.handlers.get(event);
        if (handlers) {
            handlers.forEach(h => h(data));
        }
    }

    // API Methods
    connectToGolike(auth: string) {
        this.send('connect', { auth });
    }

    startAutomation(accounts: any[], auth: string) {
        this.send('start', { accounts, auth });
    }

    stopAutomation() {
        this.send('stop', {});
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    isConnected(): boolean {
        return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
    }
}

// Singleton instance
export const golikeService = new GolikeService();

// Cookie validation for each platform
export const checkCookieFormat = (cookie: string, platform: Platform): boolean => {
    if (!cookie) return false;
    if (platform === 'instagram') {
        return cookie.includes('sessionid') && cookie.includes('ds_user_id');
    }
    if (platform === 'pinterest') {
        return cookie.includes('_auth') || cookie.includes('_pinterest_sess');
    }
    if (platform === 'twitter') {
        // Twitter: ct0 (csrf token) hoặc auth_token
        // FAKE_ONLY mode nên cookie không bắt buộc đúng format
        return cookie.includes('ct0') || cookie.includes('auth_token') || cookie.length > 10;
    }
    return false;
};

// Update cookie for a running worker
export const updateAccountCookie = (accountId: string, cookie: string, platform: Platform) => {
    golikeService.send('updateCookie', { accountId, cookie, platform });
};