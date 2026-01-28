# -*- coding: utf-8 -*-
"""
==================================================
     GOLIKE AUTO TOOL - INSTAGRAM v8.0 ULTIMATE
     GUI: Rich + Colorama + PyFiglet + Art
     LOGIC: FULL từ ig.py (965 dòng)
==================================================
"""
import json
import os
import random
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import requests  # Instagram API
import tls_client  # GoLike API

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# === IMPORT GUI LIBRARIES ===
# Rich
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.live import Live
    from rich import box
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None
    print("⚠ Cài đặt Rich để có giao diện đẹp hơn: pip install rich")

# Colorama
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    Fore = Back = Style = type('', (), {})()
    Fore.RED = Fore.GREEN = Fore.YELLOW = Fore.CYAN = Fore.MAGENTA = Fore.WHITE = ''
    Back.BLACK = ''
    Style.BRIGHT = Style.RESET_ALL = ''
    print("⚠ Cài đặt Colorama để có màu sắc: pip install colorama")

# PyFiglet (ASCII Art)
try:
    from pyfiglet import figlet_format
    HAS_PYFIGLET = True
except ImportError:
    HAS_PYFIGLET = False

# Art (Decorative text)
try:
    from art import text2art, tprint
    HAS_ART = True
except ImportError:
    HAS_ART = False

# ==================== CONFIG ====================
GOLIKE_BASE_URL = "https://gateway.golike.net/api"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ig_config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ig_log.txt")

MAX_CONSECUTIVE_FAILS = 5
MAX_WORKERS = 5

# Thời gian chờ khi hết việc (giây)
NO_JOB_WAIT_TIME = 1800  # 30 phút
ERROR_RETRY_TIME = 300    # 5 phút
GOLIKE_NO_JOB_WAIT_TIME = 32 * 60  # 32 phút - khi GoLike báo "chưa có jobs mới"

# Mobile devices để fake - 40+ devices
MOBILE_DEVICES = [
    # Samsung S Series
    {"model": "SM-S908B", "android_version": "14", "platform": "Android"},  # S22 Ultra
    {"model": "SM-S918B", "android_version": "14", "platform": "Android"},  # S23 Ultra
    {"model": "SM-S928B", "android_version": "14", "platform": "Android"},  # S24 Ultra
    {"model": "SM-G998B", "android_version": "14", "platform": "Android"},  # S21 Ultra
    {"model": "SM-S911B", "android_version": "14", "platform": "Android"},  # S23
    {"model": "SM-G991B", "android_version": "13", "platform": "Android"},  # S21
    {"model": "SM-G996B", "android_version": "13", "platform": "Android"},  # S21+
    
    # Samsung A Series
    {"model": "SM-A546B", "android_version": "14", "platform": "Android"},  # A54
    {"model": "SM-A536B", "android_version": "13", "platform": "Android"},  # A53
    {"model": "SM-A525F", "android_version": "13", "platform": "Android"},  # A52
    {"model": "SM-A556B", "android_version": "14", "platform": "Android"},  # A55
    {"model": "SM-A736B", "android_version": "13", "platform": "Android"},  # A73
    
    # Google Pixel
    {"model": "Pixel 8 Pro", "android_version": "14", "platform": "Android"},
    {"model": "Pixel 8", "android_version": "14", "platform": "Android"},
    {"model": "Pixel 7 Pro", "android_version": "13", "platform": "Android"},
    {"model": "Pixel 7", "android_version": "13", "platform": "Android"},
    {"model": "Pixel 6 Pro", "android_version": "13", "platform": "Android"},
    {"model": "Pixel 7a", "android_version": "14", "platform": "Android"},
    
    # OnePlus
    {"model": "CPH2451", "android_version": "14", "platform": "Android"},  # OnePlus 12
    {"model": "CPH2399", "android_version": "13", "platform": "Android"},  # OnePlus 11
    {"model": "OnePlus 11", "android_version": "13", "platform": "Android"},
    {"model": "CPH2501", "android_version": "14", "platform": "Android"},  # OnePlus 12R
    
    # Xiaomi
    {"model": "23117PN0BC", "android_version": "14", "platform": "Android"},  # Xiaomi 14
    {"model": "2211133C", "android_version": "13", "platform": "Android"},   # Xiaomi 13
    {"model": "23078PND5G", "android_version": "14", "platform": "Android"}, # Xiaomi 13T
    {"model": "22081212C", "android_version": "13", "platform": "Android"},  # Xiaomi 12T
    
    # Oppo
    {"model": "CPH2487", "android_version": "14", "platform": "Android"},  # Oppo Find X6
    {"model": "CPH2305", "android_version": "13", "platform": "Android"},  # Oppo Reno 10
    {"model": "CPH2523", "android_version": "14", "platform": "Android"},  # Oppo Find X7
    
    # Vivo
    {"model": "V2250", "android_version": "14", "platform": "Android"},  # Vivo X100
    {"model": "V2145", "android_version": "13", "platform": "Android"},  # Vivo X90
    
    # iPhone
    {"model": "iPhone15,2", "ios_version": "17.4", "platform": "iOS"},  # iPhone 14 Pro
    {"model": "iPhone15,3", "ios_version": "17.4", "platform": "iOS"},  # iPhone 14 Pro Max
    {"model": "iPhone14,3", "ios_version": "17.2", "platform": "iOS"},  # iPhone 13 Pro Max
    {"model": "iPhone16,1", "ios_version": "17.4", "platform": "iOS"},  # iPhone 15 Pro
    {"model": "iPhone16,2", "ios_version": "17.4", "platform": "iOS"},  # iPhone 15 Pro Max
]

HAS_FAKE_UA = False
_ua = None

# Lock cho thread-safe operations
stats_lock = Lock()

# ==================== HELPERS ====================
def get_random_user_agent():
    """Get random mobile User-Agent - 40+ devices"""
    fallback_uas = [
        # Samsung Galaxy S Series
        "Mozilla/5.0 (Linux; Android 14; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-G996B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
        
        # Samsung Galaxy A Series
        "Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-A525F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; SM-A556B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-A736B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
        
        # Google Pixel
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 7a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        
        # OnePlus
        "Mozilla/5.0 (Linux; Android 14; CPH2451) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; CPH2399) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; OnePlus 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; CPH2501) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        
        # Xiaomi
        "Mozilla/5.0 (Linux; Android 14; 23117PN0BC) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; 2211133C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; 23078PND5G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; 22081212C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
        
        # Oppo
        "Mozilla/5.0 (Linux; Android 14; CPH2487) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; CPH2305) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; CPH2523) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        
        # Vivo
        "Mozilla/5.0 (Linux; Android 14; V2250) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; V2145) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        
        # iPhone - iOS 17.x
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        
        # iPhone - iOS 16.x
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    ]
    return random.choice(fallback_uas)

def get_random_mobile_device():
    """Get random mobile device info"""
    device = random.choice(MOBILE_DEVICES).copy()
    device["user_agent"] = get_random_user_agent()
    return device

def parse_cookies(cookie_str):
    """Parse cookie string thành dictionary"""
    cookies = {}
    if not cookie_str:
        return cookies
    
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()
    
    return cookies

def get_ig_headers(username_or_url, csrftoken):
    """Tạo headers cho Instagram API - FULL HEADERS từ ig.py"""
    # Xác định referer
    if username_or_url.startswith('http'):
        referer = username_or_url
    else:
        referer = f'https://www.instagram.com/{username_or_url}/'
    
    return {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'dnt': '1',
        'origin': 'https://www.instagram.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': referer,
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="143.0.7499.193", "Chromium";v="143.0.7499.193", "Not A(Brand";v="24.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"15.0.0"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-csrftoken': csrftoken,
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': '0',
        'x-instagram-ajax': '1032506596',
        'x-requested-with': 'XMLHttpRequest',
    }

def get_golike_headers():
    """Headers cho GoLike API - MOBILE ONLY với fake UA"""
    device = get_random_mobile_device()
    ua = device["user_agent"]
    is_ios = device["platform"] == "iOS"
    
    # Randomize Chrome version
    chrome_version = random.randint(128, 131)
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
        "cache-control": "no-cache",
        "content-type": "application/json;charset=utf-8",
        "origin": "https://app.golike.net",
        "referer": "https://app.golike.net/",
        "pragma": "no-cache",
        # CRITICAL: Mobile indicators
        "sec-ch-ua-mobile": "?1",  # ALWAYS mobile
        "sec-ch-ua-platform": '"iOS"' if is_ios else '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "t": "VFZSak1rMVVXVEJOZWsweVRWRTlQUT09",
        "user-agent": ua,
    }
    
    # Android-specific headers
    if not is_ios:
        headers["sec-ch-ua"] = f'"Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}", "Not_A Brand";v="24"'
    
    return headers

def create_tls_session():
    """Tạo TLS session cho GoLike"""
    s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
    s.timeout_seconds = 30
    return s

def now():
    return datetime.now().strftime("%H:%M:%S")

def write_log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except:
        pass

def print_log(acc_name, msg, log_type="info"):
    """In log gọn gàng với màu sắc đẹp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Icon và màu sắc theo loại log
    log_styles = {
        "info": {"icon": "ℹ️", "color": Fore.CYAN, "style": ""},
        "success": {"icon": "✓", "color": Fore.GREEN, "style": Style.BRIGHT},
        "fail": {"icon": "✗", "color": Fore.RED, "style": Style.BRIGHT},
        "warn": {"icon": "⚠", "color": Fore.YELLOW, "style": ""},
        "skip": {"icon": "⊘", "color": Fore.MAGENTA, "style": ""},
        "money": {"icon": "💰", "color": Fore.YELLOW, "style": Style.BRIGHT},
        "check": {"icon": "🔍", "color": Fore.CYAN, "style": ""},
        "complete": {"icon": "🎉", "color": Fore.GREEN, "style": Style.BRIGHT},
    }
    
    style = log_styles.get(log_type, log_styles["info"])
    icon = style["icon"]
    color = style["color"]
    text_style = style["style"]
    
    # Rút gọn tên account nếu quá dài (max 12 ký tự)
    acc_display = acc_name[:12] if len(acc_name) > 12 else acc_name
    acc_display = f"{acc_display:<12}"  # Padding để align
    
    if HAS_RICH:
        from rich.text import Text
        
        log_text = Text()
        log_text.append(f"[{timestamp}] ", style="dim white")
        log_text.append(f"[{acc_display}] ", style="bold cyan")
        log_text.append(f"{icon} ", style="")
        log_text.append(msg, style=color.replace('\x1b[', '').replace('m', ''))
        
        console.print(log_text)
    else:
        full_msg = f"{Fore.WHITE}[{timestamp}]{Style.RESET_ALL} {Fore.CYAN}[{acc_display}]{Style.RESET_ALL} {color}{text_style}{icon} {msg}{Style.RESET_ALL}"
        print(full_msg)
    
    # Ghi vào file log
    write_log(f"[{acc_name}] {icon} {msg}")

# ==================== CONFIG FILE ====================
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"auth": None, "max_fails": MAX_CONSECUTIVE_FAILS}

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def load_ck(aid):
    ck_path = f"ig_ck_{aid}.txt"
    if os.path.exists(ck_path):
        try:
            with open(ck_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except:
            pass
    return None

def save_ck(aid, ck):
    with open(f"ig_ck_{aid}.txt", "w", encoding="utf-8") as f:
        f.write(ck)

# ==================== INSTAGRAM API ====================
class InstagramAPI:
    """Instagram API sử dụng requests - FULL LOGIC từ ig.py"""
    
    def __init__(self, cookies_str):
        self.cookies = parse_cookies(cookies_str)
        self.csrftoken = self.cookies.get('csrftoken', '')
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)
    
    def get_user_id(self, username):
        """Lấy user_id từ username - với retry logic"""
        url = f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}'
        headers = get_ig_headers(username, self.csrftoken)
        
        # Retry 3 lần với delay
        for attempt in range(3):
            try:
                response = self.session.get(url, headers=headers, timeout=15, allow_redirects=False)
                
                if response.status_code == 200:
                    data = response.json()
                    user_id = data['data']['user']['id']
                    return user_id
                elif response.status_code in [301, 302]:
                    print_log("IG", "Session đã hết hạn - cần nhập cookies mới", "fail")
                    return None
                elif response.status_code == 400:
                    # User không tồn tại hoặc lỗi request
                    if attempt < 2:
                        time.sleep(2)  # Đợi 2s trước khi retry
                        continue
                    return None  # Không log chi tiết, để worker xử lý
                elif response.status_code == 429:
                    # Rate limit - đợi lâu hơn
                    wait_time = 60 * (attempt + 1)
                    print_log("IG", f"Rate limit! Đợi {wait_time}s...", "warn")
                    time.sleep(wait_time)
                    continue
                else:
                    if attempt < 2:
                        time.sleep(3)
                        continue
                    print_log("IG", f"Không thể lấy user_id: HTTP {response.status_code}", "fail")
                    return None
                    
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                    continue
                print_log("IG", f"Lỗi khi lấy user_id: {str(e)[:100]}", "fail")
                return None
        
        return None
    
    def follow_user(self, username, user_id):
        """Follow user sử dụng Web API - với retry logic"""
        url = f'https://www.instagram.com/api/v1/web/friendships/{user_id}/follow/'
        headers = get_ig_headers(username, self.csrftoken)
        
        # Retry 3 lần
        for attempt in range(3):
            try:
                response = self.session.post(url, headers=headers, timeout=15, allow_redirects=False)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'ok':
                        return True, "Follow thành công"
                    else:
                        return False, f"API trả về: {data.get('status')}"
                elif response.status_code == 403:
                    return False, "Lỗi 403: CSRF token hoặc session không hợp lệ"
                elif response.status_code == 429:
                    wait_time = 60 * (attempt + 1)
                    if attempt < 2:
                        print_log("IG", f"Rate limit! Đợi {wait_time}s...", "warn")
                        time.sleep(wait_time)
                        continue
                    return False, "Lỗi 429: Rate limit - đã follow quá nhiều"
                elif response.status_code == 500:
                    # Server error - retry
                    if attempt < 2:
                        time.sleep(5)
                        continue
                    return False, "Lỗi 500: Instagram server error"
                elif response.status_code in [301, 302]:
                    return False, "Session đã hết hạn"
                else:
                    if attempt < 2:
                        time.sleep(3)
                        continue
                    return False, f"HTTP {response.status_code}"
                    
            except Exception as e:
                if attempt < 2:
                    time.sleep(3)
                    continue
                return False, f"Exception: {str(e)[:100]}"
        
        return False, "Failed after 3 attempts"
    
    def get_media_id(self, post_url):
        """Lấy media_id từ URL bài post - với retry logic"""
        # Retry 3 lần
        for attempt in range(3):
            try:
                # Extract shortcode từ URL
                # Format: https://www.instagram.com/p/SHORTCODE/ hoặc /reel/SHORTCODE/
                parts = post_url.rstrip('/').split('/')
                shortcode = parts[-1]
                
                url = f'https://www.instagram.com/api/v1/media/webinfo/?shortcode={shortcode}'
                headers = get_ig_headers('instagram', self.csrftoken)
                
                response = self.session.get(url, headers=headers, timeout=15, allow_redirects=False)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Thử các path khác nhau
                    media_id = None
                    try:
                        media_id = data['items'][0]['id']
                    except:
                        try:
                            media_id = data['data']['shortcode_media']['id']
                        except:
                            pass
                    
                    if media_id:
                        return media_id
                elif response.status_code == 429:
                    wait_time = 60 * (attempt + 1)
                    if attempt < 2:
                        print_log("IG", f"Rate limit! Đợi {wait_time}s...", "warn")
                        time.sleep(wait_time)
                        continue
                    return None
                else:
                    if attempt < 2:
                        time.sleep(3)
                        continue
                    return None
                    
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                    continue
                print_log("IG", f"Lỗi lấy media_id: {str(e)[:100]}", "fail")
                return None
        
        return None
    
    def like_post(self, media_id, post_url=""):
        """Like bài post - với retry logic"""
        url = f'https://www.instagram.com/api/v1/web/likes/{media_id}/like/'
        
        # Dùng post_url làm referer nếu có
        referer = post_url if post_url else 'https://www.instagram.com/'
        headers = get_ig_headers(referer, self.csrftoken)
        
        # Retry 3 lần
        for attempt in range(3):
            try:
                response = self.session.post(url, headers=headers, timeout=15, allow_redirects=False)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'ok':
                        return True, "Like thành công"
                    else:
                        return False, f"API trả về: {data.get('status')}"
                elif response.status_code == 403:
                    return False, "Lỗi 403: CSRF token hoặc session không hợp lệ"
                elif response.status_code == 429:
                    wait_time = 60 * (attempt + 1)
                    if attempt < 2:
                        print_log("IG", f"Rate limit! Đợi {wait_time}s...", "warn")
                        time.sleep(wait_time)
                        continue
                    return False, "Lỗi 429: Rate limit - đã like quá nhiều"
                elif response.status_code == 500:
                    if attempt < 2:
                        time.sleep(5)
                        continue
                    return False, "Lỗi 500: Instagram server error"
                elif response.status_code in [301, 302]:
                    return False, "Session đã hết hạn"
                else:
                    if attempt < 2:
                        time.sleep(3)
                        continue
                    return False, f"HTTP {response.status_code}"
                    
            except Exception as e:
                if attempt < 2:
                    time.sleep(3)
                    continue
                return False, f"Exception: {str(e)[:100]}"
        
        return False, "Failed after 3 attempts"
    
    def check_session(self):
        """Kiểm tra session có hoạt động không"""
        try:
            url = 'https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram'
            headers = get_ig_headers('instagram', self.csrftoken)
            
            response = self.session.get(url, headers=headers, timeout=10, allow_redirects=False)
            
            if response.status_code == 200:
                return True
            elif response.status_code in [301, 302]:
                return False
            else:
                return True  # Vẫn thử tiếp
                
        except:
            return False

# ==================== GOLIKE API ====================
class GoLike:
    """GoLike API - FULL LOGIC từ ig.py"""
    def __init__(self, auth, session):
        self.auth = auth
        self.s = session
    
    def _req(self, method, ep, data=None):
        h = get_golike_headers()
        
        # Xử lý auth - tự động thêm Bearer nếu chưa có
        auth = self.auth.strip()
        if not auth.lower().startswith('bearer '):
            auth = f"Bearer {auth}"
        h["authorization"] = auth
        
        url = f"{GOLIKE_BASE_URL}{ep}"
        
        for attempt in range(3):
            try:
                if method == "GET":
                    r = self.s.get(url, headers=h)
                else:
                    r = self.s.post(url, headers=h, json=data)
                
                if not r or not hasattr(r, 'status_code'):
                    time.sleep(2)
                    continue
                
                try:
                    json_data = r.json()
                    # Không log nữa - để Worker tự xử lý
                    return json_data
                except:
                    time.sleep(2)
                    continue
                    
            except Exception as e:
                time.sleep(2)
        
        return None
    
    def me(self):
        return self._req("GET", "/users/me")
    
    def accounts(self):
        return self._req("GET", "/instagram-account")
    
    def get_job(self, aid):
        result = self._req("GET", f"/advertising/publishers/instagram/jobs?instagram_account_id={aid}&data=null")
        
        # Debug logging - chỉ log khi có lỗi
        if result:
            status = result.get("status")
            
            # Chỉ log khi không có job hoặc lỗi
            if status != 200:
                message = result.get("message", "")
                print(f"{Fore.YELLOW}[DEBUG] Acc {aid}: {message[:50]}{Style.RESET_ALL}")
        
        return result
    
    def complete_job(self, aid, ad_id, instagram_users_advertising_id):
        """Complete job với đầy đủ thông tin"""
        payload = {
            "ads_id": ad_id, 
            "instagram_account_id": aid,
            "instagram_users_advertising_id": instagram_users_advertising_id
        }
        return self._req("POST", f"/advertising/publishers/instagram/complete-jobs", payload)
    
    def report_error(self, aid, ad_id, object_id, error_type=2, description="Không tìm thấy bài viết"):
        """Báo lỗi cho GoLike"""
        payload = {
            "description": description,
            "users_advertising_id": ad_id,
            "type": "ads",
            "error_type": error_type,
            "fb_id": aid,
            "provider": "instagram"
        }
        return self._req("POST", f"/report/send", [payload])  # Send as array
    
    def skip_job(self, aid, ad_id, object_id, job_type):
        """Skip job không làm được"""
        payload = {
            "ads_id": ad_id,
            "object_id": object_id,
            "account_id": aid,
            "type": job_type
        }
        return self._req("POST", f"/advertising/publishers/instagram/skip-jobs", payload)

# ==================== WORKER ====================
class Worker:
    """Worker thread - FULL LOGIC từ ig.py"""
    _no_jobs_accounts = set()  # Accounts hết việc tạm thời
    _permanently_stopped = set()  # Accounts dừng vĩnh viễn (hết việc lâu dài)
    
    def __init__(self, golike, account, cookies_str, stats, auto, min_delay, max_delay, max_fails):
        self.gl = golike
        self.acc = account
        self.aid = str(account.get("account_id") or account.get("id"))
        self.name = account.get("instagram_username") or self.aid
        self.cookies_str = cookies_str
        self.stats = stats
        self.auto = auto
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_fails = max_fails
        self.running = True
        self.consecutive_fails = 0
        self.no_job_count = 0  # Đếm số lần hết việc liên tiếp
        
        # Tạo Instagram API client
        self.ig_api = InstagramAPI(cookies_str)
    
    def run(self):
        """Chạy worker"""
        print_log(self.name, "Khởi động worker...", "info")
        
        # Kiểm tra session trước
        if not self.ig_api.check_session():
            print_log(self.name, "Session Instagram không hợp lệ", "fail")
            return
        
        print_log(self.name, "Session Instagram OK", "success")
        
        while self.running:
            try:
                # Check nếu đã dừng vĩnh viễn
                if self.aid in Worker._permanently_stopped:
                    print_log(self.name, "⏹ Account đã dừng vĩnh viễn", "warn")
                    break
                
                # Lấy job từ GoLike
                job_data = self.gl.get_job(self.aid)
                
                if not job_data or job_data.get("status") != 200:
                    # Kiểm tra nếu hết việc
                    if job_data:
                        msg = job_data.get("message", "")
                        status = job_data.get("status")
                        
                        # Kiểm tra message "hết việc"
                        if status in [400, 404] and ("chưa có jobs" in msg or "hết việc" in msg.lower() or "no job" in msg.lower()):
                            self.no_job_count += 1
                            
                            if self.no_job_count >= 3:
                                # Hết việc 3 lần liên tiếp → Dừng vĩnh viễn
                                Worker._permanently_stopped.add(self.aid)
                                print_log(self.name, f"⏹ Hết việc {self.no_job_count} lần - DỪNG VĨNH VIỄN", "warn")
                                break
                            else:
                                print_log(self.name, f"⏸ Hết việc lần {self.no_job_count}/3, chờ 5 phút...", "warn")
                                time.sleep(300)  # Đợi 5 phút
                                continue
                    
                    # Các lỗi khác
                    error_msg = job_data.get("message", "Unknown error")
                    
                    # Check nếu là message "hết job - quay lại sau 30p"
                    if "chưa có jobs mới" in error_msg.lower() or "quay lại sau" in error_msg.lower():
                        print_log(self.name, f"⏸ {error_msg}", "warn")
                        
                        # Đợi 32 phút
                        wait_time = GOLIKE_NO_JOB_WAIT_TIME
                        mins = wait_time // 60
                        print_log(self.name, f"⏳ GoLike yêu cầu đợi - Nghỉ {mins} phút...", "info")
                        
                        # Hiển thị thời gian kết thúc
                        from datetime import datetime, timedelta
                        end_time = datetime.now() + timedelta(seconds=wait_time)
                        end_time_str = end_time.strftime("%H:%M:%S")
                        print_log(self.name, f"⏰ Sẽ check lại lúc {end_time_str}", "info")
                        
                        # Countdown
                        if HAS_RICH:
                            from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
                            
                            with Progress(
                                SpinnerColumn(),
                                TextColumn("[yellow]{task.description}"),
                                BarColumn(bar_width=40),
                                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                                TextColumn("•"),
                                TimeRemainingColumn(),
                                console=console,
                                transient=False
                            ) as progress:
                                task = progress.add_task(
                                    f"[{self.name}] 💤 Nghỉ {mins}p (GoLike hết job) - Check lại lúc {end_time_str}", 
                                    total=wait_time
                                )
                                
                                for i in range(wait_time):
                                    time.sleep(1)
                                    progress.update(task, advance=1)
                                    if not self.running:
                                        break
                        else:
                            # Fallback countdown
                            import sys
                            for i in range(wait_time, 0, -1):
                                mins_left = i // 60
                                secs = i % 60
                                sys.stdout.write(f"\r{Fore.YELLOW}[{self.name}] 💤 Chờ: {mins_left}m {secs}s {Style.RESET_ALL}")
                                sys.stdout.flush()
                                time.sleep(1)
                                if not self.running:
                                    break
                            sys.stdout.write("\r" + " " * 80 + "\r")
                            sys.stdout.flush()
                        
                        print_log(self.name, f"✅ Đã nghỉ xong {mins} phút - Tiếp tục check job!", "info")
                        continue
                    
                    # Các lỗi khác - thử lại sau 5 phút
                    retry_minutes = ERROR_RETRY_TIME // 60
                    print_log(self.name, f"Lỗi API, thử lại sau {retry_minutes} phút", "warn")
                    time.sleep(ERROR_RETRY_TIME)
                    continue
                
                # Reset counter khi có job
                self.no_job_count = 0
                
                job = job_data.get("data", {})
                if not job or (isinstance(job, dict) and not job):
                    print_log(self.name, f"Không có job, chờ 30 phút...", "warn")
                    time.sleep(NO_JOB_WAIT_TIME)
                    continue
                
                # Lấy thông tin job - hỗ trợ nhiều format
                job_type = job.get("type") or job.get("job_type", "")
                ad_id = job.get("id") or job.get("ads_id") or job.get("job_id")
                link = job.get("link", "") or job.get("url", "")
                object_id = job.get("object_id", "")
                
                # Lấy instagram_users_advertising_id từ lock hoặc job
                instagram_users_advertising_id = None
                if "lock" in job_data and job_data["lock"]:
                    instagram_users_advertising_id = job_data["lock"].get("instagram_users_advertising_id")
                if not instagram_users_advertising_id:
                    instagram_users_advertising_id = ad_id  # Fallback to ad_id
                
                # Hỗ trợ follow và like
                if job_type not in ["follow", "like"]:
                    print_log(self.name, f"Bỏ qua job: {job_type}", "warn")
                    time.sleep(3)
                    continue
                
                # === XỬ LÝ FOLLOW ===
                if job_type == "follow":
                    # Parse username từ link
                    try:
                        target_username = link.rstrip('/').split('/')[-1]
                        if not target_username or target_username == 'www.instagram.com':
                            raise ValueError("Invalid username")
                    except:
                        print_log(self.name, f"Link không hợp lệ: {link}", "fail")
                        with stats_lock:
                            self.stats.fail += 1
                        continue
                    
                    print_log(self.name, f"Job: Follow @{target_username}", "info")
                    
                    # Confirm nếu chế độ manual
                    if not self.auto:
                        confirm = input(f"    Xác nhận? (y/n): ")
                        if confirm.lower() != 'y':
                            print_log(self.name, "Bỏ qua", "warn")
                            time.sleep(2)
                            continue
                    
                    # Lấy user_id
                    user_id = self.ig_api.get_user_id(target_username)
                    
                    # Delay ngẫu nhiên để tránh spam
                    time.sleep(random.uniform(1, 3))
                    
                    if not user_id:
                        self.consecutive_fails += 1
                        
                        # Báo lỗi cho GoLike nếu là lỗi 404 (user không tồn tại)
                        # Retry 3 lần trước khi báo lỗi
                        if self.consecutive_fails >= 3:
                            print_log(self.name, f"❌ User @{target_username} không tồn tại (thử {self.consecutive_fails} lần) - Skip job", "fail")
                            
                            # Report error
                            self.gl.report_error(
                                self.aid, 
                                ad_id, 
                                object_id,
                                error_type=2,
                                description="Không tìm thấy người dùng"
                            )
                            
                            # Skip job
                            self.gl.skip_job(self.aid, ad_id, object_id, "follow")
                            
                            # Reset counter và tiếp tục
                            self.consecutive_fails = 0
                            time.sleep(3)
                            continue
                        else:
                            # Chỉ log ngắn gọn khi retry
                            print_log(self.name, f"⚠ Retry lần {self.consecutive_fails}/3...", "warn")
                        
                        with stats_lock:
                            self.stats.fail += 1
                        
                        if self.consecutive_fails >= self.max_fails:
                            print_log(self.name, f"Thất bại {self.consecutive_fails} lần - Dừng", "warn")
                            break
                        
                        time.sleep(5)
                        continue
                    
                    # Follow user
                    success, msg = self.ig_api.follow_user(target_username, user_id)
                    
                    if success:
                        print_log(self.name, f"Follow @{target_username} thành công", "success")
                        
                        # Báo GoLike hoàn thành
                        time.sleep(2)
                        result = self.gl.complete_job(self.aid, ad_id, instagram_users_advertising_id)
                        
                        if result and result.get("status") == 200:
                            # Lấy thông tin tiền
                            data = result.get("data", {})
                            prices = data.get("prices", 0)
                            coin = data.get("coin")
                            
                            # Luôn hiển thị số tiền nhận được
                            if coin is not None and coin > 0:
                                print_log(self.name, f"💰 +{prices}đ | Tổng: {coin:,}đ", "success")
                            else:
                                print_log(self.name, f"💰 +{prices}đ", "success")
                            
                            with stats_lock:
                                self.stats.ok += 1
                            self.consecutive_fails = 0
                        else:
                            print_log(self.name, f"⚠ Lỗi báo GoLike", "warn")
                            with stats_lock:
                                self.stats.fail += 1
                    else:
                        print_log(self.name, f"Follow thất bại: {msg}", "fail")
                        self.consecutive_fails += 1
                        with stats_lock:
                            self.stats.fail += 1
                        
                        if self.consecutive_fails >= self.max_fails:
                            print_log(self.name, f"Thất bại {self.consecutive_fails} lần - Dừng worker", "warn")
                            break
                
                # === XỬ LÝ LIKE ===
                elif job_type == "like":
                    print_log(self.name, f"Job: Like post", "info")
                    
                    # Confirm nếu chế độ manual
                    if not self.auto:
                        confirm = input(f"    Xác nhận? (y/n): ")
                        if confirm.lower() != 'y':
                            print_log(self.name, "Bỏ qua", "warn")
                            time.sleep(2)
                            continue
                    
                    # Lấy media_id từ URL
                    media_id = self.ig_api.get_media_id(link)
                    
                    # Delay ngẫu nhiên để tránh spam
                    time.sleep(random.uniform(1, 3))
                    
                    if not media_id:
                        self.consecutive_fails += 1
                        
                        # Báo lỗi cho GoLike nếu retry 3 lần
                        if self.consecutive_fails >= 3:
                            print_log(self.name, f"❌ Post không tồn tại (thử {self.consecutive_fails} lần) - Skip job", "fail")
                            
                            # Report error
                            self.gl.report_error(
                                self.aid, 
                                ad_id, 
                                object_id,
                                error_type=2,
                                description="Không tìm thấy bài viết"
                            )
                            
                            # Skip job
                            self.gl.skip_job(self.aid, ad_id, object_id, "like")
                            
                            # Reset counter và tiếp tục
                            self.consecutive_fails = 0
                            time.sleep(3)
                            continue
                        else:
                            # Chỉ log ngắn gọn khi retry
                            print_log(self.name, f"⚠ Retry lần {self.consecutive_fails}/3...", "warn")
                        
                        with stats_lock:
                            self.stats.fail += 1
                        
                        if self.consecutive_fails >= self.max_fails:
                            print_log(self.name, f"Thất bại {self.consecutive_fails} lần - Dừng", "warn")
                            break
                        
                        time.sleep(5)
                        continue
                    
                    # Like post
                    success, msg = self.ig_api.like_post(media_id, link)
                    
                    if success:
                        print_log(self.name, f"Like post thành công", "success")
                        
                        # Báo GoLike hoàn thành
                        time.sleep(2)
                        result = self.gl.complete_job(self.aid, ad_id, instagram_users_advertising_id)
                        
                        if result and result.get("status") == 200:
                            # Lấy thông tin tiền
                            data = result.get("data", {})
                            prices = data.get("prices", 0)
                            coin = data.get("coin")
                            
                            # Luôn hiển thị số tiền nhận được
                            if coin is not None and coin > 0:
                                print_log(self.name, f"💰 +{prices}đ | Tổng: {coin:,}đ", "success")
                            else:
                                print_log(self.name, f"💰 +{prices}đ", "success")
                            
                            with stats_lock:
                                self.stats.ok += 1
                            self.consecutive_fails = 0
                        else:
                            print_log(self.name, f"⚠ Lỗi báo GoLike", "warn")
                            with stats_lock:
                                self.stats.fail += 1
                    else:
                        print_log(self.name, f"Like thất bại: {msg}", "fail")
                        self.consecutive_fails += 1
                        with stats_lock:
                            self.stats.fail += 1
                        
                        if self.consecutive_fails >= self.max_fails:
                            print_log(self.name, f"Thất bại {self.consecutive_fails} lần - Dừng worker", "warn")
                            break
                
                # Delay
                delay = random.uniform(self.min_delay, self.max_delay)
                print_log(self.name, f"Chờ {delay:.1f}s...", "info")
                time.sleep(delay)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print_log(self.name, f"❌ Lỗi không mong muốn: {str(e)[:100]}", "fail")
                time.sleep(5)
        
        print_log(self.name, "Đã dừng worker", "info")

# ==================== STATS ====================
class Stats:
    def __init__(self):
        self.ok = 0
        self.fail = 0
        self.current_acc = ""

# ==================== GUI FUNCTIONS ====================
def show_banner():
    """Banner cực đẹp với gradient và hiệu ứng"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    if HAS_RICH:
        from rich.align import Align
        from rich.panel import Panel
        from rich.text import Text
        
        # ASCII Art Instagram
        banner = """
╔════════════════════════════════════════════════════════════════╗
║   ██╗███╗   ██╗███████╗████████╗ █████╗  ██████╗ ██████╗  █████╗ ███╗   ███╗ ║
║   ██║████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██╔════╝ ██╔══██╗██╔══██╗████╗ ████║ ║
║   ██║██╔██╗ ██║███████╗   ██║   ███████║██║  ███╗██████╔╝███████║██╔████╔██║ ║
║   ██║██║╚██╗██║╚════██║   ██║   ██╔══██║██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║ ║
║   ██║██║ ╚████║███████║   ██║   ██║  ██║╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║ ║
║   ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝ ║
╚════════════════════════════════════════════════════════════════╝
        """
        
        # Gradient colors
        title_text = Text()
        colors = ["magenta", "bright_magenta", "bright_blue", "cyan", "bright_cyan"]
        lines = banner.strip().split('\n')
        
        for i, line in enumerate(lines):
            color_idx = i % len(colors)
            title_text.append(line + "\n", style=colors[color_idx])
        
        console.print(Align.center(title_text))
        
        # Info panel
        info = Text()
        info.append("🎨 ", style="bold magenta")
        info.append("AUTO GOLIKE TOOL", style="bold bright_cyan")
        info.append(" v9.0 ULTIMATE\n", style="bold yellow")
        
        info.append("\n")
        info.append("⚡ ", style="bold yellow")
        info.append("Features: ", style="bold white")
        info.append("Follow • Like • Comment • Save • Smart Retry\n", style="cyan")
        
        info.append("🎯 ", style="bold green")
        info.append("Mobile: ", style="bold white")
        info.append("40+ Real Device UAs • Advanced Fingerprinting\n", style="green")
        
        info.append("💰 ", style="bold yellow")
        info.append("Profit: ", style="bold white")
        info.append("Real-time Stats • Multi Workers • Auto Recovery", style="yellow")
        
        console.print(Panel(
            Align.center(info),
            border_style="bright_magenta",
            title="[bold yellow]⭐ INSTAGRAM AUTOMATION ⭐[/bold yellow]",
            subtitle="[italic cyan]Made with ❤️  by Expert[/italic cyan]",
            padding=(1, 4)
        ))
        
        # Separator
        separator = Text("─" * 80, style="bright_blue")
        console.print(Align.center(separator))
        console.print()
        
    else:
        # Fallback
        print(Fore.MAGENTA + Style.BRIGHT + """
╔════════════════════════════════════════════════════════════════╗
║   ██╗███╗   ██╗███████╗████████╗ █████╗  ██████╗ ██████╗  █████╗ ███╗   ███╗ ║
║   ██║████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██╔════╝ ██╔══██╗██╔══██╗████╗ ████║ ║
║   ██║██╔██╗ ██║███████╗   ██║   ███████║██║  ███╗██████╔╝███████║██╔████╔██║ ║
║   ██║██║╚██╗██║╚════██║   ██║   ██╔══██║██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║ ║
║   ██║██║ ╚████║███████║   ██║   ██║  ██║╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║ ║
║   ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝ ║
╚════════════════════════════════════════════════════════════════╝
        """ + Style.RESET_ALL)
        
        print(Fore.CYAN + Style.BRIGHT + "🎨 AUTO GOLIKE TOOL v9.0 ULTIMATE")
        print(Fore.YELLOW + "⚡ Follow • Like • Comment • Save • Smart Retry")
        print(Style.RESET_ALL + "\n")

def show_menu(title, options):
    """Show colorful menu"""
    if HAS_RICH:
        text = Text()
        text.append(f"\n📋 {title}\n\n", style="bold cyan")
        for i, opt in enumerate(options, 1):
            text.append(f"  [{i}] ", style="bold yellow")
            text.append(f"{opt}\n", style="white")
        console.print(Panel(text, border_style="cyan", padding=(1, 2)))
    else:
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*60}")
        print(f"📋 {title}")
        print('='*60 + Style.RESET_ALL)
        for i, opt in enumerate(options, 1):
            print(f"{Fore.YELLOW}  [{i}]{Style.RESET_ALL} {opt}")

def prompt(msg, required=True, hidden=False):
    """Input prompt with validation"""
    if hidden:
        from getpass import getpass
        while True:
            val = getpass(Fore.CYAN + msg + Style.RESET_ALL)
            val = val.strip()
            if not required or val:
                return val
            print(Fore.RED + "⚠ Không được để trống!" + Style.RESET_ALL)
    else:
        while True:
            val = input(Fore.CYAN + msg + Style.RESET_ALL)
            val = val.strip()
            if not required or val:
                return val
            print(Fore.RED + "⚠ Không được để trống!" + Style.RESET_ALL)

# ==================== MAIN RUNNER ====================
def run_parallel(gl, accs, cks, cfg):
    """Run parallel workers - FULL LOGIC từ ig.py"""
    
    print("\n" + "="*60)
    print(Fore.CYAN + Style.BRIGHT + "CÀI ĐẶT" + Style.RESET_ALL)
    print("="*60)
    
    max_f = cfg.get("max_fails", MAX_CONSECUTIVE_FAILS)
    
    # Chọn chế độ
    show_menu("CHẾ ĐỘ CHẠY", [
        "TỰ ĐỘNG - Chạy liên tục",
        "THỦ CÔNG - Xác nhận từng job"
    ])
    
    choice = prompt("👉 Chọn (1/2, mặc định 1): ", required=False)
    auto = choice != "2"
    
    min_d = float(prompt("⏱️  Delay nhỏ nhất (3s): ", required=False) or "3")
    max_d = float(prompt("⏱️  Delay lớn nhất (6s): ", required=False) or "6")
    
    num_workers = min(len(accs), MAX_WORKERS)
    
    # Show config
    if HAS_RICH:
        table = Table(title="⚙️  CẤU HÌNH", border_style="cyan", show_header=True)
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="yellow")
        table.add_row("📊 Số tài khoản", str(len(accs)))
        table.add_row("👷 Số workers", str(num_workers))
        table.add_row("🎯 Chế độ", "TỰ ĐỘNG" if auto else "THỦ CÔNG")
        table.add_row("⏱️  Delay", f"{min_d}-{max_d}s")
        table.add_row("🔄 Auto switch", f"{max_f} lần lỗi")
        table.add_row("📱 Job types", "Follow + Like")
        console.print(table)
    else:
        print(f"\n{Fore.CYAN}{'='*60}")
        print("⚙️  CẤU HÌNH")
        print('='*60)
        print(f"{Fore.GREEN}✓ Số tài khoản: {len(accs)}")
        print(f"✓ Số workers: {num_workers}")
        print(f"✓ Chế độ: {'TỰ ĐỘNG' if auto else 'THỦ CÔNG'}")
        print(f"✓ Delay: {min_d}-{max_d}s")
        print(f"✓ Auto switch: {max_f} lần lỗi")
        print(f"✓ Job types: Follow + Like")
        print('='*60 + Style.RESET_ALL)
    
    print(Fore.YELLOW + "\n⌨️  Nhấn Ctrl+C để dừng\n" + Style.RESET_ALL)
    
    stats = Stats()
    workers = []
    
    # Tạo workers với animation
    if HAS_RICH:
        with console.status("[bold cyan]🔧 Đang tạo workers...", spinner="dots") as status:
            for i in range(num_workers):
                idx = i % len(accs)
                acc = accs[idx]
                aid = str(acc.get("account_id") or acc.get("id"))
                ck = cks.get(aid)
                
                if not ck:
                    console.print(f"[red]⚠ Bỏ qua account {aid}: không có cookies[/red]")
                    continue
                
                status.update(f"[bold cyan]🔧 Creating worker {i+1}/{num_workers}...")
                worker = Worker(gl, acc, ck, stats, auto, min_d, max_d, max_f)
                workers.append(worker)
                time.sleep(0.2)  # Animation delay
    else:
        for i in range(num_workers):
            idx = i % len(accs)
            acc = accs[idx]
            aid = str(acc.get("account_id") or acc.get("id"))
            ck = cks.get(aid)
            
            if not ck:
                print(f"{Fore.RED}⚠ Bỏ qua account {aid}: không có cookies{Style.RESET_ALL}")
                continue
            
            worker = Worker(gl, acc, ck, stats, auto, min_d, max_d, max_f)
            workers.append(worker)
    
    if not workers:
        if HAS_RICH:
            console.print("[bold red]❌ Không có worker nào được tạo![/bold red]")
        else:
            print(f"{Fore.RED}❌ Không có worker nào được tạo!{Style.RESET_ALL}")
        return
    
    # Animation bắt đầu
    if HAS_RICH:
        from rich.panel import Panel
        from rich.text import Text
        from rich.align import Align
        
        start_info = Text()
        start_info.append("🚀 ", style="bold yellow")
        start_info.append(f"Khởi động {len(workers)} worker{'s' if len(workers) > 1 else ''}", style="bold cyan")
        start_info.append(f" • ", style="white")
        start_info.append(f"Mode: {'AUTO' if auto else 'MANUAL'}", style="bold green")
        start_info.append(f"\n⏱️  ", style="bold blue")
        start_info.append(f"Delay: {min_d}s - {max_d}s", style="white")
        start_info.append(f" • ", style="white")
        start_info.append(f"Max fails: {max_f}", style="yellow")
        
        console.print(Panel(
            Align.center(start_info),
            border_style="bright_green",
            title="[bold]⚡ STARTING ⚡[/bold]",
            padding=(1, 2)
        ))
        
        # Progress animation
        with console.status("[bold green]🔄 Initializing workers...", spinner="dots") as status:
            for i in range(len(workers)):
                time.sleep(0.3)
                status.update(f"[bold green]🔄 Worker {i+1}/{len(workers)} ready...")
        
        console.print(f"\n[bold green]✅ All workers ready! Let's go! 🎯[/bold green]\n")
    else:
        print(f"{Fore.CYAN}{'─'*60}")
        print(f"🚀 Bắt đầu với {len(workers)} workers | Mode: {'AUTO' if auto else 'MANUAL'}")
        print(f"⏱️  Delay: {min_d}s-{max_d}s | Max fails: {max_f}")
        print(f"{'─'*60}{Style.RESET_ALL}\n")
        time.sleep(1)
    
    try:
        # Chạy workers song song
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker.run) for worker in workers]
            
            for future in futures:
                future.result()
                
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⏸ Đang dừng workers...{Style.RESET_ALL}")
        
        for worker in workers:
            worker.running = False
        
        time.sleep(2)
    
    # Kết quả cuối cùng
    print(f"\n{Fore.CYAN}{'='*60}")
    print("📊 KẾT QUẢ CUỐI CÙNG")
    print('='*60 + Style.RESET_ALL)
    
    if Worker._permanently_stopped:
        print(f"\n{Fore.RED}⏹ CÁC ACCOUNT ĐÃ DỪNG VĨNH VIỄN (hết việc):{Style.RESET_ALL}")
        for aid in Worker._permanently_stopped:
            # Tìm tên account
            acc_name = aid
            for w in workers:
                if w.aid == aid:
                    acc_name = w.name
                    break
            print(f"  • {acc_name} (ID: {aid})")
        print()
    
    total = stats.ok + stats.fail
    rate = (stats.ok / total * 100) if total > 0 else 0
    
    print(f"{Fore.GREEN}✓ THÀNH CÔNG: {stats.ok}")
    print(f"{Fore.RED}✗ THẤT BẠI: {stats.fail}")
    print(f"{Fore.CYAN}TỶ LỆ: {rate:.1f}%")
    print('='*60 + Style.RESET_ALL + "\n")

# ==================== MAIN ====================
def main():
    """Main entry point"""
    show_banner()
    cfg = load_config()
    s = create_tls_session()  # TLS session cho GoLike
    
    # Nhập auth GoLike
    if not cfg.get("auth"):
        print(Fore.YELLOW + "⚠ Chưa có auth GoLike!")
        print("📝 Cách lấy: app.golike.net > F12 > Network > authorization" + Style.RESET_ALL)
        cfg["auth"] = prompt("👉 Nhập auth GoLike: ", hidden=True)
        save_config(cfg)
    
    gl = GoLike(cfg["auth"], s)
    
    # Kết nối GoLike
    if HAS_RICH:
        with console.status("[cyan]🔄 Đang kết nối GoLike...[/cyan]", spinner="dots"):
            time.sleep(1)
            me = gl.me()
    else:
        print(Fore.CYAN + "🔄 Đang kết nối GoLike..." + Style.RESET_ALL)
        me = gl.me()
    
    if not me or me.get("status") != 200:
        print(Fore.RED + "❌ Kết nối thất bại! Kiểm tra lại auth." + Style.RESET_ALL)
        cfg["auth"] = None
        save_config(cfg)
        return
    
    user = me.get("data", {}).get("username", "?")
    coin = me.get("data", {}).get("coin", 0)
    
    print(Fore.GREEN + Style.BRIGHT + f"\n✅ Đã kết nối thành công!")
    print(Fore.YELLOW + f"👤 Tài khoản: {user} | 💰 Số dư: {coin:,}đ\n" + Style.RESET_ALL)
    
    # Lấy danh sách accounts
    acc_data = gl.accounts()
    accs = acc_data.get("data", []) if acc_data else []
    
    if not accs:
        print(Fore.RED + "❌ Không có tài khoản IG nào trên GoLike!" + Style.RESET_ALL)
        return
    
    print(Fore.GREEN + f"✓ Tìm thấy {len(accs)} tài khoản Instagram\n" + Style.RESET_ALL)
    
    # Hiển thị danh sách accounts
    if HAS_RICH:
        table = Table(title="📱 DANH SÁCH TÀI KHOẢN", border_style="cyan")
        table.add_column("Index", style="yellow", width=8)
        table.add_column("Username", style="cyan")
        table.add_column("ID", style="white")
        
        for i, a in enumerate(accs):
            aid = str(a.get("account_id") or a.get("id"))
            name = a.get("instagram_username") or aid
            table.add_row(str(i), name, aid)
        
        console.print(table)
    else:
        print(f"\n{Fore.CYAN}{'='*60}")
        print("📱 DANH SÁCH TÀI KHOẢN")
        print('='*60 + Style.RESET_ALL)
        for i, a in enumerate(accs):
            aid = str(a.get("account_id") or a.get("id"))
            name = a.get("instagram_username") or aid
            print(f"{Fore.YELLOW}[{i}]{Style.RESET_ALL} {Fore.CYAN}{name}{Style.RESET_ALL} (ID: {aid})")
        print()
    
    # Chọn accounts
    print(Fore.CYAN + "📌 Chọn tài khoản để chạy:" + Style.RESET_ALL)
    print(f"{Fore.YELLOW}  • Nhập số (vd: 0, 1, 2)")
    print(f"  • Nhập nhiều số cách nhau bằng dấu phẩy (vd: 0,1,2)")
    print(f"  • Nhập 'all' để chạy tất cả{Style.RESET_ALL}")
    
    choice = prompt("👉 Chọn: ", required=False) or "all"
    choice = choice.strip().lower()
    
    selected_accs = []
    if choice == "all":
        selected_accs = accs
        print(Fore.GREEN + f"✓ Đã chọn: TẤT CẢ ({len(accs)} accounts)" + Style.RESET_ALL)
    else:
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            for idx in indices:
                if 0 <= idx < len(accs):
                    selected_accs.append(accs[idx])
            
            if not selected_accs:
                print(Fore.RED + "❌ Không có account hợp lệ!" + Style.RESET_ALL)
                return
            
            print(Fore.GREEN + f"✓ Đã chọn: {len(selected_accs)} accounts" + Style.RESET_ALL)
        except:
            print(Fore.RED + "❌ Lỗi format! Nhập lại." + Style.RESET_ALL)
            return
    
    # Load cookies cho accounts đã chọn
    cks = {}
    for a in selected_accs:
        aid = str(a.get("account_id") or a.get("id"))
        name = a.get("instagram_username") or aid
        
        ck = load_ck(aid)
        if not ck:
            print(Fore.YELLOW + f"\n⚠ Chưa có cookies cho {name}")
            print("📝 Cách lấy: F12 > Console > document.cookie")
            print("⚡ Lưu ý: Paste TOÀN BỘ cookies (sessionid, csrftoken...)" + Style.RESET_ALL)
            ck = prompt(f"👉 Nhập cookies cho {name}: ")
            save_ck(aid, ck)
        
        cks[aid] = ck
    
    # Cài đặt auto switch
    print(f"\n{Fore.CYAN}{'='*60}")
    print("CÀI ĐẶT TỰ ĐỘNG ĐỔI ACC")
    print('='*60 + Style.RESET_ALL)
    print(f"Số lần thất bại trước khi đổi: {cfg.get('max_fails', MAX_CONSECUTIVE_FAILS)}")
    
    if prompt("Thay đổi? (y/n, mặc định n): ", required=False).lower() == "y":
        try:
            cfg["max_fails"] = int(prompt("Số lần thất bại trước khi đổi acc: "))
            save_config(cfg)
            print(Fore.GREEN + f"✓ Đã cập nhật: đổi acc sau {cfg['max_fails']} lần thất bại" + Style.RESET_ALL)
        except:
            pass
    
    run_parallel(gl, selected_accs, cks, cfg)

if __name__ == "__main__":
    main()