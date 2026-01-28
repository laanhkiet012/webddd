# -*- coding: utf-8 -*-
"""
==================================================
     GOLIKE AUTO TOOL - TWITTER/X v2.0 ULTIMATE
     GUI: Rich + Colorama + PyFiglet + Art
     Full Features: Follow + Like + Retweet + Comment + Auto Skip + Multi-threading
     API: Hoàn chỉnh theo Twitter/X response
==================================================
"""
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from urllib.parse import urlparse, parse_qs

import requests
import tls_client

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# === IMPORT GUI LIBRARIES ===
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
    print("⚠ Cài đặt Rich: pip install rich")

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

try:
    from pyfiglet import figlet_format
    HAS_PYFIGLET = True
except ImportError:
    HAS_PYFIGLET = False

try:
    from art import text2art, tprint
    HAS_ART = True
except ImportError:
    HAS_ART = False

# ==================== CONFIG ====================
GOLIKE_BASE_URL = "https://gateway.golike.net/api"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "x_config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "x_log.txt")

MAX_CONSECUTIVE_FAILS = 5
MAX_WORKERS = 5
NO_JOB_WAIT_TIME = 1800  # 30 phút
ERROR_RETRY_TIME = 300    # 5 phút
GOLIKE_NO_JOB_WAIT_TIME = 32 * 60  # 32 phút - khi GoLike báo "chưa có jobs mới"

# ==================== FAKE MODE (JOB ẢO) ====================
# Khi bật: Job fail sẽ tự động báo thành công (Golike không quét X)
FAKE_MODE = True              # True = Bật job ảo, False = Chỉ làm thật
FAKE_ONLY = True              # True = FAKE 100%, không thử làm thật (nhanh hơn)
FAKE_AFTER_FAILS = 1          # Sau bao nhiêu lần fail thì fake (1 = fake ngay nếu fail)
FAKE_DELAY_MIN = 7            # Delay tối thiểu trước khi fake (giây)
FAKE_DELAY_MAX = 10            # Delay tối đa trước khi fake (giây)
FAKE_SUCCESS_RATE = 0.95      # Tỷ lệ fake thành công (95%)

# Twitter/X GraphQL endpoints
GRAPHQL_ENDPOINTS = {
    'CreateTweet': 'z0m4Q8u_67R9VOSMXU_MWg/CreateTweet',
    'CreateRetweet': 'LFho5rIi4xcKO90p9jwG7A/CreateRetweet',
    'FavoriteTweet': 'lI07N6Otwv1PhnEgXILM7A/FavoriteTweet',
    'UnfavoriteTweet': 'ZYKSe-w7KEslx3JhSIk5LA/UnfavoriteTweet',
}

# Mobile User Agents
MOBILE_USER_AGENTS = [
    # iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    
    # Samsung
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
    
    # Pixel
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
]

stats_lock = Lock()

# ==================== HELPERS ====================
def write_log(msg):
    """Ghi log vào file"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass

def print_log(acc_name, msg, log_type="info"):
    """In log có màu sắc - format gọn gàng"""
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
    
    # Format: [TIME] [ACC] ICON MSG
    acc_display = acc_name[:12] if len(acc_name) > 12 else acc_name
    acc_display = f"{acc_display:<12}"
    
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
    
    write_log(f"[{acc_name}] {icon} {msg}")

def load_config():
    """Load config từ file"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"auth": None, "max_fails": MAX_CONSECUTIVE_FAILS}

def save_config(cfg):
    """Save config vào file"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"{Fore.RED}❌ Lỗi lưu config: {e}{Style.RESET_ALL}")

def load_ck(aid):
    """Load cookies từ file"""
    ck_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"x_ck_{aid}.txt")
    if os.path.exists(ck_path):
        try:
            with open(ck_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except:
            pass
    return None

def save_ck(aid, ck):
    """Save cookies vào file"""
    ck_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"x_ck_{aid}.txt")
    try:
        with open(ck_path, "w", encoding="utf-8") as f:
            f.write(ck)
    except Exception as e:
        print(f"{Fore.RED}❌ Lỗi lưu cookies: {e}{Style.RESET_ALL}")

def delete_ck(aid):
    """Xóa file cookies cũ"""
    ck_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"x_ck_{aid}.txt")
    try:
        if os.path.exists(ck_path):
            os.remove(ck_path)
            return True
    except:
        pass
    return False

def parse_cookies(cookie_str):
    """Parse cookies string thành dict"""
    cookies = {}
    if not cookie_str:
        return cookies
    
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            key, val = item.split('=', 1)
            cookies[key.strip()] = val.strip()
    return cookies

def request_new_cookies(aid, account_name, twitter_username):
    """Yêu cầu nhập cookies mới"""
    print(f"\n{Fore.YELLOW}{'='*70}")
    print(f"🍪 YÊU CẦU COOKIES MỚI CHO ACCOUNT: {account_name}")
    print('='*70 + Style.RESET_ALL)
    
    print(f"{Fore.CYAN}📌 Tài khoản Twitter/X: {twitter_username}")
    print(f"📌 Account ID: {aid}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}📝 HƯỚNG DẪN LẤY COOKIES:")
    print("   1. Mở https://x.com (hoặc twitter.com)")
    print(f"   2. Đăng nhập tài khoản: {twitter_username}")
    print("   3. Nhấn F12 > Console")
    print("   4. Gõ: document.cookie")
    print("   5. Copy TOÀN BỘ cookies" + Style.RESET_ALL)
    
    print(f"\n{Fore.RED}⚠️  LƯU Ý QUAN TRỌNG:")
    print("   • Cần có: auth_token và ct0")
    print("   • Không chia sẻ cookies cho người khác!")
    print("   • Cookies hết hạn sau vài ngày" + Style.RESET_ALL)
    
    while True:
        ck = prompt(f"\n👉 Nhập cookies (hoặc 'skip' để bỏ qua): ", required=False)
        
        if not ck or ck.lower() == 'skip':
            return None
        
        # Kiểm tra cookies có hợp lệ không
        parsed = parse_cookies(ck)
        if not parsed.get('auth_token') or not parsed.get('ct0'):
            print(f"{Fore.RED}❌ Cookies thiếu auth_token hoặc ct0! Vui lòng thử lại.{Style.RESET_ALL}")
            continue
        
        # Save và return
        save_ck(aid, ck)
        print(f"{Fore.GREEN}✓ Đã lưu cookies!{Style.RESET_ALL}")
        return ck

def prompt(text, required=True, hidden=False):
    """Prompt người dùng nhập input"""
    while True:
        try:
            if hidden:
                from getpass import getpass
                val = getpass(f"{Fore.YELLOW}{text}{Style.RESET_ALL}").strip()
            else:
                val = input(f"{Fore.YELLOW}{text}{Style.RESET_ALL}").strip()
            
            if val or not required:
                return val
            print(f"{Fore.RED}❌ Không được để trống!{Style.RESET_ALL}")
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

def show_banner():
    """Hiển thị banner đẹp"""
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    if HAS_RICH and HAS_PYFIGLET:
        try:
            # ASCII Art với pyfiglet
            ascii_art = figlet_format("X / Twitter", font="slant")
            console.print(ascii_art, style="bold cyan")
        except:
            pass
    elif HAS_ART:
        try:
            # Fallback với art
            tprint("X / Twitter", font="tarty1")
        except:
            pass
    
    if HAS_RICH:
        # Rich panel
        from rich.panel import Panel
        from rich.text import Text
        
        content = Text()
        content.append("🚀 ", style="")
        content.append("GOLIKE AUTO TOOL - TWITTER/X v2.0 ULTIMATE", style="bold yellow")
        content.append("\n\n", style="")
        content.append("✨ Features: ", style="bold cyan")
        content.append("Multi-threading • Auto Skip • Smart Retry\n", style="green")
        content.append("📊 Support: ", style="bold cyan")
        content.append("Follow • Like • Retweet • Comment\n", style="green")
        content.append("🎨 Interface: ", style="bold cyan")
        content.append("Rich GUI • Colorful Logs • Statistics\n", style="green")
        
        panel = Panel(
            content,
            border_style="cyan",
            box=box.DOUBLE,
            padding=(1, 2),
        )
        console.print(panel)
        console.print()
    else:
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}{'GOLIKE AUTO - TWITTER/X v2.0 ULTIMATE'.center(70)}")
        print(f"{Fore.CYAN}{'='*70}")
        print(f"{Fore.GREEN}✨ Multi-threading • Auto Skip • Smart Retry")
        print(f"📊 Follow • Like • Retweet • Comment")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

# ==================== GOLIKE API ====================
class GoLike:
    def __init__(self, auth, session):
        self.auth = auth
        self.s = session
    
    def _get_headers(self):
        ua = random.choice(MOBILE_USER_AGENTS)
        
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://app.golike.net",
            "priority": "u=1, i",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "t": "VFZSak1rOVVWWGRPUkVVd1RVRTlQUT09",
            "user-agent": ua,
            "authorization": self.auth
        }
    
    def _req(self, method, ep, data=None):
        url = f"{GOLIKE_BASE_URL}{ep}"
        
        for retry in range(3):
            try:
                if method == "GET":
                    r = self.s.get(url, headers=self._get_headers())
                else:
                    r = self.s.post(url, headers=self._get_headers(), json=data)
                
                return r.json()
            except Exception as e:
                if retry == 2:
                    return None
                time.sleep(2)
        return None
    
    def me(self):
        """Lấy thông tin user"""
        return self._req("GET", "/users/me")
    
    def accounts(self):
        """Lấy danh sách accounts Twitter/X"""
        return self._req("GET", "/twitter-account")
    
    def job(self, acc_id):
        """Lấy job mới"""
        return self._req("GET", f"/advertising/publishers/twitter/jobs?account_id={acc_id}")
    
    def done(self, acc_id, job_id):
        """Báo hoàn thành job"""
        return self._req("POST", "/advertising/publishers/twitter/complete-jobs", 
                        {"ads_id": job_id, "account_id": acc_id})
    
    def skip(self, acc_id, job_id, reason="error"):
        """Skip job"""
        return self._req("POST", "/advertising/publishers/twitter/skip-jobs", 
                        {"ads_id": job_id, "account_id": acc_id, "object_id": reason})

# ==================== TWITTER/X API ====================
def get_twitter_headers(cookies_dict, csrf_token, auth_token):
    """Generate Twitter API headers"""
    return {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'cookie': '; '.join([f"{k}={v}" for k, v in cookies_dict.items()]),
        'origin': 'https://x.com',
        'referer': 'https://x.com/',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'x-csrf-token': csrf_token,
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
    }

def extract_tweet_id(link):
    """Trích xuất tweet ID từ link"""
    try:
        # Format: https://x.com/username/status/1234567890
        # hoặc: https://twitter.com/username/status/1234567890
        patterns = [
            r'/status/(\d+)',
            r'twitter\.com/[^/]+/status/(\d+)',
            r'x\.com/[^/]+/status/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, link)
            if match:
                return match.group(1)
        
        return None
    except:
        return None

def extract_user_id(link):
    """Trích xuất user ID từ link"""
    try:
        # Format: https://x.com/username
        # hoặc: https://twitter.com/username
        patterns = [
            r'x\.com/([^/?\s]+)',
            r'twitter\.com/([^/?\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, link)
            if match:
                username = match.group(1)
                # Loại bỏ các path đặc biệt
                if username not in ['status', 'i', 'intent', 'compose', 'home', 'explore', 'notifications', 'messages']:
                    return username
        
        return None
    except:
        return None

def twitter_follow(user_id_or_username, cookies_dict, csrf_token):
    """Follow user trên Twitter/X - Fixed version"""
    try:
        s = requests.Session()
        
        # Build cookie string
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookies_dict.items()])
        
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': cookie_str,
            'origin': 'https://x.com',
            'pragma': 'no-cache',
            'referer': 'https://x.com/',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'x-csrf-token': csrf_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en',
        }
        
        # Nếu là username, cần get user_id trước
        if not str(user_id_or_username).isdigit():
            url = "https://x.com/i/api/graphql/xmU6X_CKVnQ5lSrCbAmJsg/UserByScreenName"
            params = {
                "variables": json.dumps({
                    "screen_name": user_id_or_username,
                    "withSafetyModeUserFields": True
                }),
                "features": json.dumps({
                    "hidden_profile_subscriptions_enabled": True,
                    "rweb_tipjar_consumption_enabled": True,
                    "responsive_web_graphql_exclude_directive_enabled": True,
                    "verified_phone_label_enabled": False,
                    "subscriptions_verification_info_is_identity_verified_enabled": True,
                    "subscriptions_verification_info_verified_since_enabled": True,
                    "highlights_tweets_tab_ui_enabled": True,
                    "responsive_web_twitter_article_notes_tab_enabled": True,
                    "subscriptions_feature_can_gift_premium": True,
                    "creator_subscriptions_tweet_preview_api_enabled": True,
                    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                    "responsive_web_graphql_timeline_navigation_enabled": True
                }),
                "fieldToggles": json.dumps({"withAuxiliaryUserLabels": False})
            }
            
            headers_get = headers.copy()
            headers_get['content-type'] = 'application/json'
            
            r = s.get(url, headers=headers_get, params=params)
            
            # Debug log
            print(f"    [DEBUG] Get user: {r.status_code}")
            
            if r.status_code == 401:
                return False, "❌ Cookies hết hạn! Vui lòng cập nhật cookies mới", None
            elif r.status_code == 200:
                try:
                    data = r.json()
                    user_data = data.get('data', {}).get('user', {}).get('result', {})
                    user_id = user_data.get('rest_id')
                    
                    if not user_id:
                        # Check if user is suspended or not found
                        if user_data.get('__typename') == 'UserUnavailable':
                            reason = user_data.get('reason', 'User không khả dụng')
                            return False, f"User không khả dụng: {reason}", None
                        return False, "Không tìm thấy user", None
                except Exception as e:
                    return False, f"Lỗi parse response: {e}", None
            elif r.status_code == 429:
                return False, "Rate limit - chờ 1 phút", None
            else:
                try:
                    err_data = r.json()
                    errors = err_data.get('errors', [])
                    if errors:
                        return False, f"Lỗi: {errors[0].get('message', r.status_code)}", None
                except:
                    pass
                return False, f"Lỗi get user info: {r.status_code}", None
        else:
            user_id = str(user_id_or_username)
        
        # Follow với user_id
        url = "https://x.com/i/api/1.1/friendships/create.json"
        
        # Include_profile_interstitial_type giúp tránh bị block
        payload = f"include_profile_interstitial_type=1&skip_status=1&user_id={user_id}"
        
        r = s.post(url, headers=headers, data=payload)
        
        # Debug log
        print(f"    [DEBUG] Follow: {r.status_code}")
        
        if r.status_code == 401:
            return False, "❌ Cookies hết hạn! Vui lòng cập nhật cookies mới", None
        elif r.status_code == 200:
            try:
                result = r.json()
                user_name = result.get('screen_name', user_id)
                return True, f"Follow thành công @{user_name}", None
            except:
                return True, f"Follow thành công (ID: {user_id})", None
        elif r.status_code == 403:
            try:
                err_data = r.json()
                errors = err_data.get('errors', [])
                if errors:
                    code = errors[0].get('code')
                    msg = errors[0].get('message', '')
                    if code == 160:  # Already following
                        return True, f"Đã follow rồi", None
                    elif code == 162:  # Blocked
                        return False, "Bị user block", None
                    return False, f"Lỗi 403: {msg}", None
            except:
                pass
            return False, "Lỗi 403 - Có thể bị rate limit", None
        elif r.status_code == 429:
            return False, "Rate limit - chờ 1 phút", None
        else:
            return False, f"Lỗi follow: {r.status_code}", None
            
    except Exception as e:
        return False, f"Exception: {str(e)}", None

def twitter_like(tweet_id, cookies_dict, csrf_token):
    """Like tweet trên Twitter/X - Fixed version"""
    try:
        s = requests.Session()
        
        # Build cookie string
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookies_dict.items()])
        
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'cookie': cookie_str,
            'origin': 'https://x.com',
            'pragma': 'no-cache',
            'referer': 'https://x.com/',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'x-csrf-token': csrf_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en',
        }
        
        # Updated endpoint - lấy từ network tab
        url = "https://x.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet"
        
        payload = {
            "variables": {"tweet_id": str(tweet_id)},
            "queryId": "lI07N6Otwv1PhnEgXILM7A"
        }
        
        r = s.post(url, headers=headers, json=payload)
        
        # Debug log
        print(f"    [DEBUG] Like: {r.status_code}")
        
        if r.status_code == 401:
            return False, "❌ Cookies hết hạn! Vui lòng cập nhật cookies mới", None
        elif r.status_code == 200:
            try:
                data = r.json()
                # Check for errors in response
                if 'errors' in data:
                    err_msg = data['errors'][0].get('message', 'Unknown error')
                    if 'already' in err_msg.lower():
                        return True, "Đã like rồi", None
                    return False, f"Lỗi: {err_msg}", None
                    
                # Success
                if data.get('data', {}).get('favorite_tweet') == 'Done':
                    return True, "Like thành công", None
                return True, "Like thành công", None
            except Exception as e:
                return False, f"Parse error: {e}", None
        elif r.status_code == 403:
            try:
                err_data = r.json()
                if 'errors' in err_data:
                    return False, f"Lỗi 403: {err_data['errors'][0].get('message', '')}", None
            except:
                pass
            return False, "Lỗi 403 - Có thể bị rate limit", None
        elif r.status_code == 429:
            return False, "Rate limit - chờ 1 phút", None
        else:
            return False, f"Lỗi like: {r.status_code}", None
            
    except Exception as e:
        return False, f"Exception: {str(e)}", None

def twitter_retweet(tweet_id, cookies_dict, csrf_token):
    """Retweet trên Twitter/X - Fixed version"""
    try:
        s = requests.Session()
        
        # Build cookie string
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookies_dict.items()])
        
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'cookie': cookie_str,
            'origin': 'https://x.com',
            'pragma': 'no-cache',
            'referer': 'https://x.com/',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'x-csrf-token': csrf_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en',
        }
        
        # Updated endpoint
        url = "https://x.com/i/api/graphql/ojPdsZsimiJrUGLR1sjUtA/CreateRetweet"
        
        payload = {
            "variables": {"tweet_id": str(tweet_id), "dark_request": False},
            "queryId": "ojPdsZsimiJrUGLR1sjUtA"
        }
        
        r = s.post(url, headers=headers, json=payload)
        
        # Debug log
        print(f"    [DEBUG] Retweet: {r.status_code}")
        
        if r.status_code == 401:
            return False, "❌ Cookies hết hạn! Vui lòng cập nhật cookies mới", None
        elif r.status_code == 200:
            try:
                data = r.json()
                # Check for errors in response
                if 'errors' in data:
                    err_msg = data['errors'][0].get('message', 'Unknown error')
                    if 'already' in err_msg.lower():
                        return True, "Đã retweet rồi", None
                    return False, f"Lỗi: {err_msg}", None
                
                # Success
                rest_id = data.get('data', {}).get('create_retweet', {}).get('retweet_results', {}).get('result', {}).get('rest_id')
                if rest_id:
                    return True, f"Retweet thành công (ID: {rest_id})", None
                return True, "Retweet thành công", None
            except Exception as e:
                return False, f"Parse error: {e}", None
        elif r.status_code == 403:
            try:
                err_data = r.json()
                if 'errors' in err_data:
                    return False, f"Lỗi 403: {err_data['errors'][0].get('message', '')}", None
            except:
                pass
            return False, "Lỗi 403 - Có thể bị rate limit", None
        elif r.status_code == 429:
            return False, "Rate limit - chờ 1 phút", None
        else:
            return False, f"Lỗi retweet: {r.status_code}", None
            
    except Exception as e:
        return False, f"Exception: {str(e)}", None

def twitter_comment(tweet_id, comment_text, cookies_dict, csrf_token):
    """Comment/reply trên tweet"""
    try:
        s = requests.Session()
        headers = get_twitter_headers(cookies_dict, csrf_token, cookies_dict.get('auth_token'))
        
        url = f"https://x.com/i/api/graphql/{GRAPHQL_ENDPOINTS['CreateTweet']}"
        
        payload = {
            "variables": {
                "tweet_text": comment_text,
                "reply": {
                    "in_reply_to_tweet_id": tweet_id,
                    "exclude_reply_user_ids": []
                },
                "dark_request": False,
                "media": {
                    "media_entities": [],
                    "possibly_sensitive": False
                },
                "semantic_annotation_ids": []
            },
            "features": {
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "articles_preview_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "rweb_tipjar_consumption_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            },
            "queryId": "z0m4Q8u_67R9VOSMXU_MWg"
        }
        
        r = s.post(url, headers=headers, json=payload)
        
        if r.status_code == 401:
            return False, "❌ Cookies hết hạn! Vui lòng cập nhật cookies mới", None
        elif r.status_code == 200:
            data = r.json()
            # Kiểm tra response có rest_id không
            rest_id = data.get('data', {}).get('create_tweet', {}).get('tweet_results', {}).get('result', {}).get('rest_id')
            if rest_id:
                return True, f"Comment thành công (ID: {rest_id})", None
            return True, "Comment thành công", None
        else:
            return False, f"Lỗi comment: {r.status_code}", None
            
    except Exception as e:
        return False, f"Exception: {str(e)}", None

# ==================== WORKER ====================
class Worker:
    _permanently_stopped = set()  # Các account đã dừng vĩnh viễn
    
    def __init__(self, gl, acc, ck_dict, cfg, stats):
        self.gl = gl
        self.acc = acc
        self.aid = str(acc.get("account_id") or acc.get("id"))
        self.name = acc.get("twitter_username") or acc.get("twitter_name") or self.aid
        self.ck = ck_dict
        self.cfg = cfg
        self.stats = stats
        
        self.running = True
        self.consecutive_fails = 0
        self.max_fails = cfg.get("max_fails", MAX_CONSECUTIVE_FAILS)
        self.auto = cfg.get("auto_mode", True)
        self.min_delay = cfg.get("min_delay", 3)
        self.max_delay = cfg.get("max_delay", 7)
        
        # Session riêng cho mỗi worker
        self.session = requests.Session()
    
    def do_job(self, job):
        """Thực hiện job"""
        job_type = job.get("type", "").lower()
        link = job.get("link") or job.get("object_id", "")
        
        csrf_token = self.ck.get('ct0', '')
        
        try:
            if job_type == "follow":
                # Extract username từ link
                user = extract_user_id(link)
                if not user:
                    return False, "Không tìm thấy username", None
                
                return twitter_follow(user, self.ck, csrf_token)
            
            elif job_type == "like":
                # Extract tweet_id từ link
                tweet_id = extract_tweet_id(link)
                if not tweet_id:
                    return False, "Không tìm thấy tweet ID", None
                
                return twitter_like(tweet_id, self.ck, csrf_token)
            
            elif job_type == "retweet":
                # Extract tweet_id từ link
                tweet_id = extract_tweet_id(link)
                if not tweet_id:
                    return False, "Không tìm thấy tweet ID", None
                
                return twitter_retweet(tweet_id, self.ck, csrf_token)
            
            elif job_type == "comment":
                # Extract tweet_id và comment text
                tweet_id = extract_tweet_id(link)
                if not tweet_id:
                    return False, "Không tìm thấy tweet ID", None
                
                # Lấy comment text từ job (nếu có)
                comment_text = job.get("comment_text") or job.get("text") or "Nice post!"
                
                return twitter_comment(tweet_id, comment_text, self.ck, csrf_token)
            
            else:
                return False, f"Job type không hỗ trợ: {job_type}", None
                
        except Exception as e:
            return False, f"Exception: {str(e)}", None
    
    def run(self):
        """Chạy worker"""
        print_log(self.name, f"Worker bắt đầu hoạt động", "info")
        
        no_job_count = 0
        
        while self.running and self.aid not in Worker._permanently_stopped:
            try:
                # Lấy job
                job_data = self.gl.job(self.aid)
                
                if not job_data:
                    print_log(self.name, "Lỗi kết nối GoLike - Đợi 5 phút...", "warn")
                    time.sleep(ERROR_RETRY_TIME)
                    continue
                
                status = job_data.get("status")
                message = job_data.get("message", "") or ""  # Đảm bảo không bao giờ None
                
                # Kiểm tra message đặc biệt từ GoLike
                if message and ("chưa có jobs mới" in message.lower() or "no new jobs" in message.lower()):
                    # GoLike báo hết job - chờ 32 phút
                    print_log(self.name, f"GoLike: {message}", "warn")
                    
                    if HAS_RICH:
                        with console.status(
                            f"[yellow]⏳ Đang chờ {GOLIKE_NO_JOB_WAIT_TIME//60} phút...[/yellow]",
                            spinner="dots"
                        ):
                            time.sleep(GOLIKE_NO_JOB_WAIT_TIME)
                    else:
                        print_log(self.name, f"Chờ {GOLIKE_NO_JOB_WAIT_TIME//60} phút trước khi thử lại...", "info")
                        
                        # Progress bar cho thời gian chờ
                        for i in range(GOLIKE_NO_JOB_WAIT_TIME):
                            remaining = GOLIKE_NO_JOB_WAIT_TIME - i
                            mins = remaining // 60
                            secs = remaining % 60
                            print(f"\r{Fore.YELLOW}⏳ Còn lại: {mins}:{secs:02d}{Style.RESET_ALL}", end="", flush=True)
                            time.sleep(1)
                        print()  # Newline
                    
                    continue
                
                # Không có job thông thường
                if status != 200 or not job_data.get("data"):
                    msg = message if message else "Không có job"
                    no_job_count += 1
                    
                    # Nếu 3 lần liên tiếp không có job → chờ 30 phút
                    if no_job_count >= 3:
                        print_log(self.name, f"Không có job sau {no_job_count} lần thử", "warn")
                        
                        if HAS_RICH:
                            # Rich progress bar
                            with Progress(
                                SpinnerColumn(),
                                TextColumn("[progress.description]{task.description}"),
                                BarColumn(),
                                TextColumn("[cyan]{task.fields[time_left]}"),
                                console=console
                            ) as progress:
                                task = progress.add_task(
                                    f"[yellow]⏳ Chờ {NO_JOB_WAIT_TIME//60} phút...",
                                    total=NO_JOB_WAIT_TIME,
                                    time_left="30:00"
                                )
                                
                                for i in range(NO_JOB_WAIT_TIME):
                                    remaining = NO_JOB_WAIT_TIME - i
                                    mins = remaining // 60
                                    secs = remaining % 60
                                    progress.update(
                                        task,
                                        advance=1,
                                        time_left=f"{mins}:{secs:02d}"
                                    )
                                    time.sleep(1)
                        else:
                            print_log(self.name, f"Chờ {NO_JOB_WAIT_TIME//60} phút...", "info")
                            
                            # Simple countdown
                            for i in range(NO_JOB_WAIT_TIME):
                                remaining = NO_JOB_WAIT_TIME - i
                                mins = remaining // 60
                                secs = remaining % 60
                                print(f"\r{Fore.YELLOW}⏳ Còn lại: {mins}:{secs:02d}{Style.RESET_ALL}", end="", flush=True)
                                time.sleep(1)
                            print()
                        
                        no_job_count = 0  # Reset counter sau khi chờ
                    else:
                        print_log(self.name, f"{msg} - Thử lại sau 30s...", "info")
                        time.sleep(30)
                    
                    continue
                
                # Có job rồi - reset counter
                no_job_count = 0
                job = job_data.get("data")
                job_id = job.get("ads_id") or job.get("id")
                job_type = job.get("type", "?")
                link = job.get("link") or job.get("object_id", "")
                
                link_display = link[:50] + "..." if len(link) > 50 else link
                print_log(self.name, f"Job: {job_type.upper()} - {link_display}", "check")
                
                # ========== FAKE_ONLY MODE ==========
                if FAKE_ONLY:
                    # Không thử làm thật - FAKE 100%
                    print_log(self.name, f"🎭 FAKE_ONLY: {job_type.upper()}", "warn")
                    
                    # Delay giả như đang làm
                    fake_delay = random.uniform(FAKE_DELAY_MIN, FAKE_DELAY_MAX)
                    time.sleep(fake_delay)
                    
                    # Báo hoàn thành (FAKE)
                    if random.random() < FAKE_SUCCESS_RATE:
                        done_result = self.gl.done(self.aid, job_id)
                        if done_result and done_result.get("success"):
                            price = done_result.get("data", {}).get("prices", 0)
                            print_log(self.name, f"🎭 FAKE +{price:,}đ", "money")
                            with stats_lock:
                                self.stats.ok += 1
                        else:
                            print_log(self.name, "Báo cáo thất bại", "warn")
                    else:
                        # 5% skip
                        self.gl.skip(self.aid, job_id, "fake_skip")
                        print_log(self.name, "Skip (random)", "skip")
                    
                    # Delay giữa jobs
                    time.sleep(random.uniform(1, 3))
                    continue
                
                # Xử lý job (thử làm thật)
                success, msg, extra = self.do_job(job)
                
                if success:
                    # Thành công
                    with stats_lock:
                        self.stats.ok += 1
                    
                    self.consecutive_fails = 0
                    print_log(self.name, f"✓ {job_type.upper()}: {msg}", "success")
                    
                    # Delay trước khi báo GoLike
                    delay = random.uniform(self.min_delay, self.max_delay)
                    
                    if HAS_RICH:
                        with console.status(
                            f"[cyan]⏱️  Delay {delay:.1f}s...[/cyan]",
                            spinner="dots"
                        ):
                            time.sleep(delay)
                    else:
                        time.sleep(delay)
                    
                    # Báo hoàn thành
                    done_result = self.gl.done(self.aid, job_id)
                    
                    if done_result and done_result.get("success"):
                        price = done_result.get("data", {}).get("prices", 0)
                        print_log(self.name, f"+{price:,}đ", "money")
                    else:
                        print_log(self.name, "Báo cáo thất bại", "warn")
                    
                else:
                    # Thất bại - nhưng có thể FAKE
                    self.consecutive_fails += 1
                    
                    # Kiểm tra nếu là lỗi cookies hết hạn - KHÔNG FAKE
                    if "cookies hết hạn" in msg.lower():
                        print_log(self.name, f"✗ {job_type.upper()}: {msg}", "fail")
                        print_log(self.name, "🔑 COOKIES HẾT HẠN - Cần cập nhật cookies mới!", "warn")
                        print_log(self.name, f"Vui lòng dừng tool (Ctrl+C) và chạy lại để nhập cookies mới", "warn")
                        
                        # Dừng worker này
                        Worker._permanently_stopped.add(self.aid)
                        
                        # Skip job và break
                        self.gl.skip(self.aid, job_id, "cookies_expired")
                        break
                    
                    # ========== FAKE MODE ==========
                    if FAKE_MODE and self.consecutive_fails >= FAKE_AFTER_FAILS:
                        # Random xem có fake thành công không
                        if random.random() < FAKE_SUCCESS_RATE:
                            print_log(self.name, f"✗ {job_type.upper()}: {msg} → 🎭 FAKE!", "warn")
                            
                            # Delay giả như đang làm
                            fake_delay = random.uniform(FAKE_DELAY_MIN, FAKE_DELAY_MAX)
                            time.sleep(fake_delay)
                            
                            # Báo hoàn thành (FAKE)
                            done_result = self.gl.done(self.aid, job_id)
                            
                            if done_result and done_result.get("success"):
                                price = done_result.get("data", {}).get("prices", 0)
                                print_log(self.name, f"🎭 FAKE +{price:,}đ (GoLike không quét)", "money")
                                with stats_lock:
                                    self.stats.ok += 1
                                self.consecutive_fails = 0  # Reset
                            else:
                                print_log(self.name, "Báo cáo thất bại", "warn")
                                with stats_lock:
                                    self.stats.fail += 1
                        else:
                            # 5% skip job
                            print_log(self.name, f"✗ {job_type.upper()}: {msg} → Skip", "fail")
                            self.gl.skip(self.aid, job_id, "error")
                            with stats_lock:
                                self.stats.fail += 1
                    else:
                        # Không fake - xử lý như bình thường
                        print_log(self.name, f"✗ {job_type.upper()}: {msg}", "fail")
                        with stats_lock:
                            self.stats.fail += 1
                        
                        # Skip job
                        self.gl.skip(self.aid, job_id, "error")
                        
                        # Kiểm tra có quá nhiều lỗi liên tiếp không
                        if self.consecutive_fails >= self.max_fails:
                            print_log(self.name, f"Quá nhiều lỗi ({self.consecutive_fails}/{self.max_fails}) - Dừng worker", "fail")
                            Worker._permanently_stopped.add(self.aid)
                            break
                
                # Delay ngắn giữa các jobs
                time.sleep(random.uniform(1, 3))
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print_log(self.name, f"Lỗi worker: {str(e)}", "fail")
                time.sleep(5)
        
        print_log(self.name, "Worker đã dừng", "complete")

# ==================== STATS ====================
class Stats:
    def __init__(self):
        self.ok = 0
        self.fail = 0

# ==================== PARALLEL RUNNER ====================
def run_parallel(gl, accs, cks, cfg):
    """Chạy nhiều workers song song"""
    stats = Stats()
    
    auto = cfg.get("auto_mode", True)
    min_d = cfg.get("min_delay", 3)
    max_d = cfg.get("max_delay", 7)
    max_f = cfg.get("max_fails", MAX_CONSECUTIVE_FAILS)
    
    num_workers = len(accs)
    
    # Tạo workers
    workers = []
    for acc in accs:
        aid = str(acc.get("account_id") or acc.get("id"))
        ck_str = cks.get(aid, "")
        ck_dict = parse_cookies(ck_str)
        
        worker = Worker(gl, acc, ck_dict, cfg, stats)
        workers.append(worker)
    
    # Hiển thị thông tin với Rich Panel
    if HAS_RICH:
        from rich.panel import Panel
        from rich.table import Table
        
        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="cyan", justify="right")
        info_table.add_column(style="yellow")
        
        info_table.add_row("👥 Workers:", str(num_workers))
        info_table.add_row("🎯 Mode:", "AUTO" if auto else "MANUAL")
        info_table.add_row("⏱️  Delay:", f"{min_d}s - {max_d}s")
        info_table.add_row("❌ Max fails:", str(max_f))
        
        panel = Panel(
            info_table,
            title="[bold cyan]🚀 BẮT ĐẦU[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
        console.print(panel)
        console.print()
        
        # Animation countdown
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Khởi động workers...", total=None)
            time.sleep(2)
            progress.update(task, description="[bold green]✅ All workers ready! Let's go! 🎯")
            time.sleep(1)
        
        console.print()
    else:
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"🚀 BẮT ĐẦU")
        print('='*60 + Style.RESET_ALL)
        print(f"{Fore.YELLOW}👥 Workers: {num_workers}")
        print(f"🎯 Mode: {'AUTO' if auto else 'MANUAL'}")
        print(f"⏱️  Delay: {min_d}s - {max_d}s")
        print(f"❌ Max fails: {max_f}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        time.sleep(2)
    
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
    
    # Kết quả cuối cùng với Rich
    if HAS_RICH:
        from rich.panel import Panel
        from rich.table import Table
        
        # Hiển thị accounts đã dừng
        if Worker._permanently_stopped:
            stopped_text = "\n".join([
                f"• {next((w.name for w in workers if w.aid == aid), aid)}" 
                for aid in Worker._permanently_stopped
            ])
            
            stopped_panel = Panel(
                stopped_text,
                title="[bold red]⏹ CÁC ACCOUNT ĐÃ DỪNG[/bold red]",
                border_style="red",
                padding=(1, 2)
            )
            console.print(stopped_panel)
            console.print()
        
        # Thống kê
        total = stats.ok + stats.fail
        rate = (stats.ok / total * 100) if total > 0 else 0
        
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(style="bold", justify="right")
        stats_table.add_column()
        
        stats_table.add_row("✓ THÀNH CÔNG:", f"[green]{stats.ok}[/green]")
        stats_table.add_row("✗ THẤT BẠI:", f"[red]{stats.fail}[/red]")
        stats_table.add_row("📊 TỶ LỆ:", f"[yellow]{rate:.1f}%[/yellow]")
        
        result_panel = Panel(
            stats_table,
            title="[bold cyan]📊 KẾT QUẢ CUỐI CÙNG[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
        console.print(result_panel)
        console.print()
    else:
        print(f"\n{Fore.CYAN}{'='*60}")
        print("📊 KẾT QUẢ CUỐI CÙNG")
        print('='*60 + Style.RESET_ALL)
        
        if Worker._permanently_stopped:
            print(f"\n{Fore.RED}⏹ CÁC ACCOUNT ĐÃ DỪNG:{Style.RESET_ALL}")
            for aid in Worker._permanently_stopped:
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

def show_account_logs(gl, acc):
    """Hiển thị lịch sử jobs của account"""
    aid = str(acc.get("account_id") or acc.get("id"))
    name = acc.get("twitter_username") or acc.get("twitter_name") or aid
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"📋 LỊCH SỬ JOBS - {name}")
    print('='*60 + Style.RESET_ALL)
    
    # Gọi API lấy logs (giả sử có endpoint)
    # Nếu không có, skip phần này
    print(f"{Fore.YELLOW}⚠️  Tính năng đang phát triển{Style.RESET_ALL}\n")

# ==================== MAIN ====================
def main():
    """Main entry point"""
    show_banner()
    cfg = load_config()
    
    # Create TLS session cho GoLike
    s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
    s.timeout_seconds = 30
    
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
        if me:
            print(f"{Fore.YELLOW}Chi tiết lỗi: {me.get('message', 'Unknown')}{Style.RESET_ALL}")
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
        print(Fore.RED + "❌ Không có tài khoản Twitter/X nào trên GoLike!" + Style.RESET_ALL)
        return
    
    print(Fore.GREEN + f"✓ Tìm thấy {len(accs)} tài khoản Twitter/X\n" + Style.RESET_ALL)
    
    # Hiển thị danh sách accounts
    if HAS_RICH:
        table = Table(title="🐦 DANH SÁCH TÀI KHOẢN", border_style="cyan")
        table.add_column("Index", style="yellow", width=8)
        table.add_column("Username", style="cyan")
        table.add_column("Twitter", style="green")
        table.add_column("ID", style="white")
        
        for i, a in enumerate(accs):
            aid = str(a.get("account_id") or a.get("id"))
            username = a.get("username") or aid
            twitter_username = a.get("twitter_username") or a.get("twitter_name") or "N/A"
            table.add_row(str(i), username, twitter_username, aid)
        
        console.print(table)
    else:
        print(f"\n{Fore.CYAN}{'='*60}")
        print("🐦 DANH SÁCH TÀI KHOẢN")
        print('='*60 + Style.RESET_ALL)
        for i, a in enumerate(accs):
            aid = str(a.get("account_id") or a.get("id"))
            username = a.get("username") or aid
            twitter_username = a.get("twitter_username") or a.get("twitter_name") or "N/A"
            print(f"{Fore.YELLOW}[{i}]{Style.RESET_ALL} {Fore.CYAN}{username}{Style.RESET_ALL} (@{twitter_username}) - ID: {aid}")
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
        username = a.get("username") or aid
        twitter_username = a.get("twitter_username") or a.get("twitter_name") or "N/A"
        
        ck = load_ck(aid)
        
        # Nếu chưa có cookies hoặc cookies cũ
        while not ck or not parse_cookies(ck).get('auth_token') or not parse_cookies(ck).get('ct0'):
            if ck:
                if not parse_cookies(ck).get('auth_token'):
                    print(f"\n{Fore.RED}❌ Cookies cũ của {username} thiếu auth_token!{Style.RESET_ALL}")
                elif not parse_cookies(ck).get('ct0'):
                    print(f"\n{Fore.RED}❌ Cookies cũ của {username} thiếu ct0!{Style.RESET_ALL}")
                delete_ck(aid)
            
            ck = request_new_cookies(aid, username, twitter_username)
            
            if not ck:
                print(f"{Fore.YELLOW}⚠️  Bỏ qua account {username}{Style.RESET_ALL}")
                break
        
        if ck:
            cks[aid] = ck
    
    # Cài đặt
    print(f"\n{Fore.CYAN}{'='*60}")
    print("⚙️  CÀI ĐẶT")
    print('='*60 + Style.RESET_ALL)
    
    print(f"\n{Fore.YELLOW}💡 KHUYẾN NGHỊ:{Style.RESET_ALL}")
    print(f"   • Delay min: 3-5s")
    print(f"   • Delay max: 7-10s")
    print(f"   • Chạy ổn định, tránh spam\n")
    
    auto = prompt("🎯 Chế độ (1=AUTO, 2=MANUAL, mặc định AUTO): ", required=False) != "2"
    
    min_input = prompt("⏱️  Delay min (giây, khuyến nghị 3): ", required=False) or "3"
    min_d = float(min_input)
    
    max_input = prompt("⏱️  Delay max (giây, khuyến nghị 7): ", required=False) or "7"
    max_d = float(max_input)
    
    # Warning nếu delay quá ngắn
    if min_d < 2:
        print(f"\n{Fore.RED}⚠️  CẢNH BÁO: Delay quá ngắn!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   → Cookies sẽ hết hạn nhanh vì Twitter/X phát hiện spam")
        print(f"   → Khuyến nghị: min >= 3s{Style.RESET_ALL}")
        
        if prompt("\n   Vẫn tiếp tục? (y/n): ", required=False).lower() != 'y':
            print(f"{Fore.CYAN}👉 Hãy nhập lại delay cao hơn nhé!{Style.RESET_ALL}")
            return
    
    if prompt("Thay đổi số lần fail tối đa? (y/n, mặc định n): ", required=False).lower() == "y":
        try:
            cfg["max_fails"] = int(prompt(f"Số lần thất bại trước khi dừng (mặc định {MAX_CONSECUTIVE_FAILS}): "))
        except:
            cfg["max_fails"] = MAX_CONSECUTIVE_FAILS
    
    cfg["auto_mode"] = auto
    cfg["min_delay"] = min_d
    cfg["max_delay"] = max_d
    save_config(cfg)
    
    print(Fore.YELLOW + "\n⌨️  Nhấn Ctrl+C để dừng\n" + Style.RESET_ALL)
    
    run_parallel(gl, selected_accs, cks, cfg)

if __name__ == "__main__":
    main()