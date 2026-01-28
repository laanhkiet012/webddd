/**
 * GOLIKE DASHBOARD - Node.js Backend Server
 * Real API implementation for Instagram & Pinterest automation
 * 
 * Based on: ig.py & pinterest_golike.py reference
 */

import express from 'express';
import http from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import fetch from 'node-fetch';
import cors from 'cors';

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ server });

app.use(cors());
app.use(express.json());

// ==================== CONFIG ====================
const GOLIKE_BASE_URL = "https://gateway.golike.net/api";

const MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
];

// ==================== UTILS ====================
const getRandomUA = () => MOBILE_USER_AGENTS[Math.floor(Math.random() * MOBILE_USER_AGENTS.length)];
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function parseCookies(cookieStr) {
    const cookies = {};
    if (!cookieStr) return cookies;
    cookieStr.split(';').forEach(item => {
        const [key, value] = item.trim().split('=');
        if (key && value) cookies[key.trim()] = value.trim();
    });
    return cookies;
}

// ==================== GOLIKE API ====================
class GolikeAPI {
    constructor(auth) {
        this.auth = auth.startsWith('Bearer') ? auth : `Bearer ${auth}`;
    }

    getHeaders() {
        const ua = getRandomUA();
        const isIOS = ua.includes('iPhone');
        return {
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br",
            "authorization": this.auth,
            "content-type": "application/json;charset=utf-8",
            "origin": "https://app.golike.net",
            "referer": "https://app.golike.net/",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": isIOS ? '"iOS"' : '"Android"',
            "t": "VFZSak1rMVVXVEJOZWsweVRWRTlQUT09",
            "user-agent": ua,
        };
    }

    async request(method, endpoint, data = null) {
        const url = `${GOLIKE_BASE_URL}${endpoint}`;
        const options = {
            method,
            headers: this.getHeaders(),
        };
        if (data) options.body = JSON.stringify(data);

        for (let attempt = 0; attempt < 3; attempt++) {
            try {
                const response = await fetch(url, options);
                return await response.json();
            } catch (e) {
                if (attempt < 2) await sleep(2000);
            }
        }
        return null;
    }

    async me() {
        return this.request("GET", "/users/me");
    }

    async getInstagramAccounts() {
        return this.request("GET", "/instagram-account");
    }

    async getPinterestAccounts() {
        return this.request("GET", "/pinterest-account");
    }

    async getInstagramJob(accountId) {
        return this.request("GET", `/advertising/publishers/instagram/jobs?instagram_account_id=${accountId}&data=null`);
    }

    async getPinterestJob(accountId) {
        return this.request("GET", `/advertising/publishers/pinterest/jobs?account_id=${accountId}`);
    }

    async completeInstagramJob(accountId, adsId, instagramUsersAdvertisingId) {
        return this.request("POST", "/advertising/publishers/instagram/complete-jobs", {
            ads_id: adsId,
            instagram_account_id: accountId,
            instagram_users_advertising_id: instagramUsersAdvertisingId
        });
    }

    async completePinterestJob(accountId, adsId, objectId) {
        return this.request("POST", "/advertising/publishers/pinterest/complete-jobs", {
            account_id: accountId,
            ads_id: adsId,
            object_id: objectId
        });
    }

    async skipJob(platform, accountId, adsId, objectId, jobType) {
        const endpoint = platform === 'instagram'
            ? "/advertising/publishers/instagram/skip-jobs"
            : "/advertising/publishers/pinterest/skip-jobs";
        return this.request("POST", endpoint, {
            ads_id: adsId,
            object_id: objectId,
            account_id: accountId,
            type: jobType
        });
    }
}

// ==================== INSTAGRAM API ====================
class InstagramAPI {
    constructor(cookiesStr) {
        this.cookies = parseCookies(cookiesStr);
        this.csrftoken = this.cookies.csrftoken || '';
        this.cookieHeader = cookiesStr;
    }

    getHeaders(referer = 'https://www.instagram.com/') {
        return {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': this.cookieHeader,
            'dnt': '1',
            'origin': 'https://www.instagram.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': referer,
            'sec-ch-prefers-color-scheme': 'dark',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not A(Brand";v="24"',
            'sec-ch-ua-full-version-list': '"Google Chrome";v="131.0.0.0", "Chromium";v="131.0.0.0", "Not A(Brand";v="24.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"15.0.0"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'x-asbd-id': '359341',
            'x-csrftoken': this.csrftoken,
            'x-ig-app-id': '936619743392459',
            'x-ig-www-claim': '0',
            'x-instagram-ajax': '1032506596',
            'x-requested-with': 'XMLHttpRequest',
        };
    }

    async getUserId(username) {
        const url = `https://www.instagram.com/api/v1/users/web_profile_info/?username=${username}`;
        for (let attempt = 0; attempt < 3; attempt++) {
            try {
                const response = await fetch(url, {
                    headers: this.getHeaders(`https://www.instagram.com/${username}/`),
                    redirect: 'manual'
                });
                if (response.status === 200) {
                    const data = await response.json();
                    return data?.data?.user?.id || null;
                }
                if (response.status === 429) await sleep(60000);
                else await sleep(3000);
            } catch (e) {
                await sleep(2000);
            }
        }
        return null;
    }

    async followUser(username, userId) {
        const url = `https://www.instagram.com/api/v1/web/friendships/${userId}/follow/`;
        for (let attempt = 0; attempt < 3; attempt++) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: this.getHeaders(`https://www.instagram.com/${username}/`),
                    redirect: 'manual'
                });
                if (response.status === 200) {
                    const data = await response.json();
                    if (data.status === 'ok') return { success: true, message: 'Follow thành công' };
                    return { success: false, message: `API: ${data.status}` };
                }
                if (response.status === 429) {
                    await sleep(60000 * (attempt + 1));
                    continue;
                }
                if (response.status === 403) return { success: false, message: 'Session hết hạn' };
                await sleep(3000);
            } catch (e) {
                await sleep(3000);
            }
        }
        return { success: false, message: 'Failed after 3 attempts' };
    }

    async getMediaId(postUrl) {
        try {
            const shortcode = postUrl.replace(/\/$/, '').split('/').pop();
            const url = `https://www.instagram.com/api/v1/media/webinfo/?shortcode=${shortcode}`;
            const response = await fetch(url, { headers: this.getHeaders(postUrl) });
            if (response.status === 200) {
                const data = await response.json();
                return data?.items?.[0]?.id || data?.data?.shortcode_media?.id || null;
            }
        } catch (e) { }
        return null;
    }

    async likePost(mediaId, postUrl = '') {
        const url = `https://www.instagram.com/api/v1/web/likes/${mediaId}/like/`;
        for (let attempt = 0; attempt < 3; attempt++) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: this.getHeaders(postUrl || 'https://www.instagram.com/'),
                    redirect: 'manual'
                });
                if (response.status === 200) {
                    const data = await response.json();
                    if (data.status === 'ok') return { success: true, message: 'Like thành công' };
                    return { success: false, message: `API: ${data.status}` };
                }
                if (response.status === 429) await sleep(60000 * (attempt + 1));
                else await sleep(3000);
            } catch (e) {
                await sleep(3000);
            }
        }
        return { success: false, message: 'Failed after 3 attempts' };
    }

    async checkSession() {
        try {
            const url = 'https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram';
            const response = await fetch(url, { headers: this.getHeaders(), redirect: 'manual' });
            return response.status === 200;
        } catch (e) {
            return false;
        }
    }
}

// ==================== PINTEREST API ====================
class PinterestAPI {
    constructor(cookiesStr) {
        this.cookies = parseCookies(cookiesStr);
        this.csrftoken = this.cookies.csrftoken || '';
        this.cookieHeader = cookiesStr;
        this.userAgent = getRandomUA();
    }

    getHeaders() {
        return {
            'accept': 'application/json, text/javascript, */*, q=0.01',
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': this.cookieHeader,
            'origin': 'https://www.pinterest.com',
            'referer': 'https://www.pinterest.com/',
            'user-agent': this.userAgent,
            'x-csrftoken': this.csrftoken,
            'x-requested-with': 'XMLHttpRequest',
        };
    }

    async followUser(userId) {
        const url = 'https://www.pinterest.com/resource/UserFollowResource/create/';
        const payload = new URLSearchParams({
            source_url: '/',
            data: JSON.stringify({ options: { user_id: String(userId) }, context: {} })
        });

        for (let attempt = 0; attempt < 3; attempt++) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: this.getHeaders(),
                    body: payload,
                    redirect: 'manual'
                });
                if (response.status === 200) {
                    const data = await response.json();
                    const res = data?.resource_response;
                    if (res?.status === 'success' && res?.code === 0) {
                        return { success: true, message: `Follow ${res?.data?.username || userId} thành công` };
                    }
                    return { success: false, message: res?.message || 'API error' };
                }
                if (response.status === 429) await sleep(30000 * (attempt + 1));
                else await sleep(3000);
            } catch (e) {
                await sleep(3000);
            }
        }
        return { success: false, message: 'Failed after 3 attempts' };
    }

    async checkSession() {
        try {
            const response = await fetch('https://www.pinterest.com/', {
                headers: { 'user-agent': this.userAgent, cookie: this.cookieHeader }
            });
            return !response.url.includes('login');
        } catch (e) {
            return true;
        }
    }
}

// ==================== WORKER ====================
class Worker {
    constructor(golike, account, cookie, platform, broadcast) {
        this.golike = golike;
        this.account = account;
        this.accountId = String(account.account_id || account.id);
        this.username = account.instagram_username || account.username || account.pinterest_username || this.accountId;
        this.cookie = cookie;
        this.platform = platform;
        this.broadcast = broadcast;
        this.running = false;
        this.consecutiveFails = 0;
        this.noJobCount = 0;

        // Create platform API
        if (platform === 'instagram') {
            this.api = new InstagramAPI(cookie);
        } else {
            this.api = new PinterestAPI(cookie);
        }
    }

    log(message, type = 'info') {
        this.broadcast({
            type: 'log',
            accountName: this.username,
            message,
            logType: type,
            timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false })
        });
    }

    async start() {
        this.running = true;
        this.log('Khởi động worker...', 'info');

        // Check session
        const sessionOk = await this.api.checkSession();
        if (!sessionOk) {
            this.log('Session không hợp lệ - cần đổi cookie', 'fail');
            this.broadcast({ type: 'accountStatus', accountId: this.accountId, status: 'die', message: 'Session hết hạn' });
            return;
        }
        this.log('Session OK', 'success');

        while (this.running) {
            try {
                await this.processJob();
                // Delay between jobs
                const delay = 8000 + Math.random() * 5000;
                await sleep(delay);
            } catch (e) {
                this.log(`Lỗi: ${e.message}`, 'fail');
                await sleep(5000);
            }
        }
    }

    async processJob() {
        // Get job from Golike
        const jobData = this.platform === 'instagram'
            ? await this.golike.getInstagramJob(this.accountId)
            : await this.golike.getPinterestJob(this.accountId);

        if (!jobData || jobData.status !== 200) {
            const msg = jobData?.message || 'No job';
            if (msg.includes('chưa có jobs') || msg.includes('hết việc')) {
                this.noJobCount++;
                if (this.noJobCount >= 3) {
                    this.log(`Hết việc ${this.noJobCount} lần - Dừng worker`, 'warn');
                    this.running = false;
                    this.broadcast({ type: 'accountStatus', accountId: this.accountId, status: 'waiting', message: 'Hết việc' });
                    return;
                }
                this.log(`Hết việc lần ${this.noJobCount}/3, chờ 5 phút...`, 'warn');
                await sleep(300000); // 5 min
            } else {
                this.log(`API: ${msg}`, 'warn');
                await sleep(60000); // 1 min
            }
            return;
        }

        this.noJobCount = 0;
        const job = jobData.data;
        if (!job || (typeof job === 'object' && Object.keys(job).length === 0)) {
            this.log('Không có job mới', 'warn');
            await sleep(60000);
            return;
        }

        const jobType = job.type || job.job_type || '';
        const adsId = job.id || job.ads_id;
        const link = job.link || job.url || '';
        const objectId = job.object_id || '';
        const instagramUsersAdvertisingId = jobData.lock?.instagram_users_advertising_id || adsId;

        this.broadcast({ type: 'accountStatus', accountId: this.accountId, status: 'working', message: `Đang làm: ${jobType.toUpperCase()}` });

        // Process based on type
        if (this.platform === 'instagram') {
            await this.processInstagramJob(jobType, adsId, link, objectId, instagramUsersAdvertisingId);
        } else {
            await this.processPinterestJob(jobType, adsId, link, objectId);
        }
    }

    async processInstagramJob(jobType, adsId, link, objectId, instagramUsersAdvertisingId) {
        if (jobType === 'follow') {
            const targetUsername = link.replace(/\/$/, '').split('/').pop();
            this.log(`Job: Follow @${targetUsername}`, 'info');

            // Get user ID
            const userId = await this.api.getUserId(targetUsername);
            await sleep(1000 + Math.random() * 2000);

            if (!userId) {
                this.consecutiveFails++;
                if (this.consecutiveFails >= 3) {
                    this.log(`User @${targetUsername} không tồn tại - Skip`, 'fail');
                    await this.golike.skipJob('instagram', this.accountId, adsId, objectId, 'follow');
                    this.consecutiveFails = 0;
                }
                return;
            }

            // Follow
            const result = await this.api.followUser(targetUsername, userId);
            if (result.success) {
                this.log(`Follow @${targetUsername} thành công`, 'success');
                await sleep(2000);

                // Complete job
                const completeResult = await this.golike.completeInstagramJob(this.accountId, adsId, instagramUsersAdvertisingId);
                if (completeResult?.status === 200) {
                    const prices = completeResult.data?.prices || 0;
                    const coin = completeResult.data?.coin;
                    this.log(`Đã làm xong FOLLOW -> Chờ duyệt (+${prices}đ)`, 'money');
                    this.broadcast({ type: 'stats', jobsDone: 1, money: prices, pending: 1 });
                    this.consecutiveFails = 0;
                } else {
                    this.log('Lỗi báo Golike', 'warn');
                }
            } else {
                this.log(`Follow thất bại: ${result.message} - Skip job`, 'fail');
                // Skip job ngay để lấy job mới
                await this.golike.skipJob('instagram', this.accountId, adsId, objectId, 'follow');
                this.consecutiveFails++;
            }
        } else if (jobType === 'like') {
            this.log('Job: Like post', 'info');

            const mediaId = await this.api.getMediaId(link);
            await sleep(1000 + Math.random() * 2000);

            if (!mediaId) {
                this.consecutiveFails++;
                if (this.consecutiveFails >= 3) {
                    this.log('Post không tồn tại - Skip', 'fail');
                    await this.golike.skipJob('instagram', this.accountId, adsId, objectId, 'like');
                    this.consecutiveFails = 0;
                }
                return;
            }

            const result = await this.api.likePost(mediaId, link);
            if (result.success) {
                this.log('Like thành công', 'success');
                await sleep(2000);

                const completeResult = await this.golike.completeInstagramJob(this.accountId, adsId, instagramUsersAdvertisingId);
                if (completeResult?.status === 200) {
                    const prices = completeResult.data?.prices || 0;
                    this.log(`Đã làm xong LIKE -> Chờ duyệt (+${prices}đ)`, 'money');
                    this.broadcast({ type: 'stats', jobsDone: 1, money: prices, pending: 1 });
                    this.consecutiveFails = 0;
                }
            } else {
                this.log(`Like thất bại: ${result.message} - Skip job`, 'fail');
                // Skip job ngay để lấy job mới
                await this.golike.skipJob('instagram', this.accountId, adsId, objectId, 'like');
                this.consecutiveFails++;
            }
        }

        this.broadcast({ type: 'accountStatus', accountId: this.accountId, status: 'active', message: 'Đã gửi duyệt' });
    }

    async processPinterestJob(jobType, adsId, link, objectId) {
        if (jobType === 'follow') {
            const userId = objectId;
            this.log(`Job: Follow Pinterest user ${userId}`, 'info');

            const result = await this.api.followUser(userId);
            if (result.success) {
                this.log(result.message, 'success');
                await sleep(2000);

                const completeResult = await this.golike.completePinterestJob(this.accountId, adsId, objectId);
                if (completeResult?.status === 200) {
                    const prices = completeResult.data?.prices || 0;
                    this.log(`Đã làm xong FOLLOW -> Chờ duyệt (+${prices}đ)`, 'money');
                    this.broadcast({ type: 'stats', jobsDone: 1, money: prices, pending: 1 });
                }
            } else {
                this.log(`Follow thất bại: ${result.message}`, 'fail');
            }
        }

        this.broadcast({ type: 'accountStatus', accountId: this.accountId, status: 'active', message: 'Đã gửi duyệt' });
    }

    stop() {
        this.running = false;
        this.log('Đã dừng worker', 'warn');
    }
}

// ==================== WEBSOCKET & STATE ====================
const workers = new Map();
let wsClients = new Set();

function broadcast(data) {
    const message = JSON.stringify(data);
    wsClients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message);
        }
    });
}

wss.on('connection', (ws) => {
    console.log('Client connected');
    wsClients.add(ws);

    ws.on('message', async (message) => {
        try {
            const data = JSON.parse(message);
            await handleMessage(ws, data);
        } catch (e) {
            console.error('Message error:', e);
        }
    });

    ws.on('close', () => {
        wsClients.delete(ws);
        console.log('Client disconnected');
    });
});

async function handleMessage(ws, data) {
    const { action, payload } = data;

    if (action === 'connect') {
        const { auth } = payload;
        const golike = new GolikeAPI(auth);

        // Get profile
        const profile = await golike.me();
        if (profile?.status === 200 && profile?.data) {
            ws.send(JSON.stringify({ type: 'profile', data: profile.data }));
            broadcast({ type: 'log', accountName: 'System', message: `Xin chào ${profile.data.username}. Số dư: ${profile.data.coin}`, logType: 'success' });
        }

        // Get accounts
        const igAccounts = await golike.getInstagramAccounts();
        const pinAccounts = await golike.getPinterestAccounts();

        const accounts = [];
        if (igAccounts?.data) {
            igAccounts.data.forEach(acc => {
                accounts.push({
                    id: String(acc.account_id || acc.id),
                    username: acc.instagram_username || 'Unknown',
                    platform: 'instagram',
                    status: 'active'
                });
            });
        }
        if (pinAccounts?.data) {
            pinAccounts.data.forEach(acc => {
                accounts.push({
                    id: String(acc.id),
                    username: acc.username || acc.pinterest_username || 'Unknown',
                    platform: 'pinterest',
                    status: 'active'
                });
            });
        }

        ws.send(JSON.stringify({ type: 'accounts', data: accounts }));
        broadcast({ type: 'log', accountName: 'System', message: `Đã tải ${accounts.length} tài khoản`, logType: 'info' });

        // Store golike instance
        ws.golike = golike;
    }

    if (action === 'start') {
        const { accounts, auth } = payload;
        const golike = ws.golike || new GolikeAPI(auth);

        broadcast({ type: 'log', accountName: 'System', message: `Bắt đầu chạy tool với ${accounts.length} tài khoản...`, logType: 'success' });

        for (const acc of accounts) {
            if (!acc.cookie) {
                broadcast({ type: 'log', accountName: acc.username, message: 'Chưa nhập cookie - bỏ qua', logType: 'warn' });
                continue;
            }

            const worker = new Worker(golike, acc, acc.cookie, acc.platform, broadcast);
            workers.set(acc.id, worker);
            worker.start(); // Run async
        }
    }

    if (action === 'stop') {
        workers.forEach(worker => worker.stop());
        workers.clear();
        broadcast({ type: 'log', accountName: 'System', message: 'Đã dừng tất cả', logType: 'warn' });
    }
}

// ==================== HTTP ENDPOINTS ====================
app.get('/health', (req, res) => {
    res.json({ status: 'ok', workers: workers.size });
});

// ==================== START SERVER ====================
const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
    console.log(`
╔═══════════════════════════════════════════════╗
║     GOLIKE DASHBOARD - Backend Server         ║
║     Port: ${PORT}                                  ║
║     WebSocket: ws://localhost:${PORT}              ║
╚═══════════════════════════════════════════════╝
    `);
});
