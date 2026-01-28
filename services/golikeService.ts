import { GOLIKE_BASE_URL, MOBILE_USER_AGENTS } from '../constants';
import { Platform } from '../types';

const getRandomUA = () => MOBILE_USER_AGENTS[Math.floor(Math.random() * MOBILE_USER_AGENTS.length)];

const getHeaders = (auth: string) => {
    return {
        "accept": "application/json, text/plain, */*",
        "authorization": auth.startsWith('Bearer') ? auth : `Bearer ${auth}`,
        "content-type": "application/json;charset=utf-8",
        "t": "VFZSak1rMVVXVEJOZWsweVRWRTlQUT09", 
        "user-agent": getRandomUA(),
    };
};

export const fetchUserProfile = async (auth: string) => {
    try {
        // Real fetch attempt
        const response = await fetch(`${GOLIKE_BASE_URL}/users/me`, {
            method: 'GET',
            headers: getHeaders(auth)
        });
        if (!response.ok) throw new Error("Failed");
        return await response.json();
    } catch (error) {
        // Fallback for UI demo only if real fetch fails (CORS usually blocks this in browser)
        console.warn("API Error (likely CORS). Using demo data.");
        return {
            status: 200,
            data: { username: "gl_farmer_vip", coin: 0 }
        };
    }
};

export const fetchAccounts = async (auth: string, platform: Platform) => {
    const endpoint = platform === 'instagram' ? '/instagram-account' : '/pinterest-account';
    try {
        const response = await fetch(`${GOLIKE_BASE_URL}${endpoint}`, {
            method: 'GET',
            headers: getHeaders(auth)
        });
        if (!response.ok) throw new Error("Failed");
        return await response.json();
    } catch (error) {
        // Returning realistic demo data based on user request (1 Pin, specific IGs)
        if (platform === 'instagram') {
            return { status: 200, data: [
                { id: 101, instagram_username: "ig.verified.ok", account_id: 101 }, // Good acc
                { id: 102, instagram_username: "ig.checkpoint.user", account_id: 102 }, // Bad acc (simulation)
                { id: 103, instagram_username: "ig.farming.pro", account_id: 103 } // Good acc
            ]};
        } else {
            // User said "Pin t thêm có 1 acc thôi"
            return { status: 200, data: [
                { id: 201, username: "pinterest_queen", pinterest_username: "pinterest_queen" }
            ]};
        }
    }
};

export const getJob = async (auth: string, accountId: string, platform: Platform) => {
    // Simulate delay
    await new Promise(r => setTimeout(r, 1000));

    // Logic: 30% chance of "No Job" (Hết job)
    // In real code, this fetches from API.
    const random = Math.random();
    
    if (random < 0.3) {
        return { status: 404, message: "Hết job rồi", data: null };
    }

    const price = platform === 'instagram' ? 35 : 50;
    
    return {
        status: 200,
        data: {
            id: `JOB_${Math.floor(Math.random() * 999999)}`,
            link: "https://example.com",
            type: Math.random() > 0.5 ? 'follow' : 'like',
            object_id: `OBJ_${Math.floor(Math.random() * 999999)}`,
            price: price,
            price_after_cost: price
        }
    };
};

export const checkCookieFormat = (cookie: string, platform: Platform): boolean => {
    if (!cookie) return false;
    if (platform === 'instagram') {
        return cookie.includes('sessionid') && cookie.includes('ds_user_id');
    }
    if (platform === 'pinterest') {
        return cookie.includes('_auth') || cookie.includes('_pinterest_sess');
    }
    return false;
};