# -*- coding: utf-8 -*-
"""
==================================================
     GOLIKE AUTO TOOL - PINTEREST v2.0 ULTIMATE
     GUI: Rich + Colorama + PyFiglet + Art
     Full Features: Follow + Auto Skip + Multi-threading
     API: Hoàn chỉnh theo Pinterest response
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
from urllib.parse import urlparse

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
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pinterest_config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pinterest_log.txt")

MAX_CONSECUTIVE_FAILS = 5
MAX_WORKERS = 5
NO_JOB_WAIT_TIME = 1800  # 30 phút
ERROR_RETRY_TIME = 300    # 5 phút
GOLIKE_NO_JOB_WAIT_TIME = 32 * 60  # 32 phút - khi GoLike báo "chưa có jobs mới"

# Mobile devices để fake
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
    # Rút gọn tên account nếu quá dài (max 12 ký tự)
    acc_display = acc_name[:12] if len(acc_name) > 12 else acc_name
    acc_display = f"{acc_display:<12}"  # Padding để align
    
    if HAS_RICH:
        # Sử dụng Rich để in với format đẹp
        from rich.text import Text
        
        log_text = Text()
        log_text.append(f"[{timestamp}] ", style="dim white")
        log_text.append(f"[{acc_display}] ", style="bold cyan")
        log_text.append(f"{icon} ", style="")
        log_text.append(msg, style=color.replace('\x1b[', '').replace('m', ''))
        
        console.print(log_text)
    else:
        # Fallback cho terminal không hỗ trợ Rich
        full_msg = f"{Fore.WHITE}[{timestamp}]{Style.RESET_ALL} {Fore.CYAN}[{acc_display}]{Style.RESET_ALL} {color}{text_style}{icon} {msg}{Style.RESET_ALL}"
        print(full_msg)
    
    # Ghi vào file log (không có màu)
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
    ck_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"pinterest_ck_{aid}.txt")
    if os.path.exists(ck_path):
        try:
            with open(ck_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except:
            pass
    return None

def save_ck(aid, ck):
    """Save cookies vào file"""
    ck_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"pinterest_ck_{aid}.txt")
    try:
        with open(ck_path, "w", encoding="utf-8") as f:
            f.write(ck)
    except Exception as e:
        print(f"{Fore.RED}❌ Lỗi lưu cookies: {e}{Style.RESET_ALL}")

def delete_ck(aid):
    """Xóa file cookies cũ"""
    ck_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"pinterest_ck_{aid}.txt")
    try:
        if os.path.exists(ck_path):
            os.remove(ck_path)
            return True
    except:
        pass
    return False

def request_new_cookies(aid, account_name, pinterest_username):
    """Yêu cầu nhập cookies mới"""
    print(f"\n{Fore.YELLOW}{'='*70}")
    print(f"🍪 YÊU CẦU COOKIES MỚI CHO ACCOUNT: {account_name}")
    print('='*70 + Style.RESET_ALL)
    
    print(f"{Fore.CYAN}📌 Tài khoản Pinterest: {pinterest_username}")
    print(f"📌 Account ID: {aid}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}📝 HƯỚNG DẪN LẤY COOKIES:")
    print("   1. Mở https://pinterest.com")
    print(f"   2. Đăng nhập tài khoản: {pinterest_username}")
    print("   3. Nhấn F12 > Console")
    print("   4. Gõ: document.cookie")
    print("   5. Copy TOÀN BỘ cookies" + Style.RESET_ALL)
    
    print(f"\n{Fore.GREEN}💡 TIP: Chạy script test trước: python test_pinterest_cookies.py{Style.RESET_ALL}")
    
    while True:
        ck = prompt(f"\n👉 Paste cookies cho {account_name} (hoặc 'skip' để bỏ qua): ", required=False)
        
        if ck.lower() == 'skip':
            return None
        
        if not ck:
            print(f"{Fore.RED}❌ Cookies không được để trống!{Style.RESET_ALL}")
            continue
        
        # Validate cookies có csrftoken không
        cookies_dict = parse_cookies(ck)
        
        # Check required cookies
        missing_cookies = []
        if not cookies_dict.get('csrftoken'):
            missing_cookies.append('csrftoken')
        if not cookies_dict.get('_auth'):
            missing_cookies.append('_auth')
        
        if missing_cookies:
            print(f"{Fore.RED}❌ Cookies thiếu: {', '.join(missing_cookies)}!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 Hãy copy TOÀN BỘ cookies từ Pinterest!{Style.RESET_ALL}")
            
            retry = prompt("Thử lại? (y/n): ", required=False)
            if retry.lower() != 'y':
                return None
            continue
        
        # Test cookies nếu muốn
        test_now = prompt(f"{Fore.CYAN}🧪 Test cookies ngay? (y/n, mặc định y): {Style.RESET_ALL}", required=False)
        if test_now.lower() != 'n':
            print(f"{Fore.CYAN}🔄 Đang test cookies...{Style.RESET_ALL}")
            
            try:
                import requests as req_test
                session = req_test.Session()
                session.cookies.update(cookies_dict)
                
                response = session.get('https://www.pinterest.com/', timeout=10)
                
                if response.status_code == 200 and 'login' not in response.url:
                    print(f"{Fore.GREEN}✅ Cookies hợp lệ! Session đang hoạt động!{Style.RESET_ALL}")
                elif 'login' in response.url:
                    print(f"{Fore.RED}❌ Cookies đã hết hạn! Pinterest redirect về login{Style.RESET_ALL}")
                    retry = prompt("Thử lại với cookies khác? (y/n): ", required=False)
                    if retry.lower() != 'y':
                        return None
                    continue
                else:
                    print(f"{Fore.YELLOW}⚠️  Status: {response.status_code} - Cookies có thể không hợp lệ{Style.RESET_ALL}")
                    use_anyway = prompt("Sử dụng cookies này? (y/n): ", required=False)
                    if use_anyway.lower() != 'y':
                        continue
            
            except Exception as e:
                print(f"{Fore.RED}❌ Lỗi test: {e}{Style.RESET_ALL}")
                use_anyway = prompt("Sử dụng cookies này? (y/n): ", required=False)
                if use_anyway.lower() != 'y':
                    continue
        
        # Lưu cookies
        save_ck(aid, ck)
        print(f"{Fore.GREEN}✅ Đã lưu cookies mới!{Style.RESET_ALL}")
        return ck
    
    return None

def parse_cookies(cookie_str):
    """Parse cookie string thành dict"""
    cookies = {}
    if not cookie_str:
        return cookies
    
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()
    
    return cookies

def extract_username_from_link(link):
    """Extract username từ Pinterest link"""
    try:
        parsed = urlparse(link)
        path = parsed.path.strip('/')
        if path:
            return path.split('/')[0]
        return None
    except:
        return None

# ==================== PINTEREST API ====================
class PinterestAPI:
    """Pinterest API handler với đầy đủ headers theo response thật"""
    
    def __init__(self, cookies_str):
        self.cookies = parse_cookies(cookies_str)
        self.csrftoken = self.cookies.get('csrftoken', '')
        
        # Validate csrftoken
        if not self.csrftoken:
            raise ValueError("❌ Cookies thiếu csrftoken! Hãy lấy lại cookies đầy đủ từ Pinterest")
        
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)
        self.user_agent = random.choice(MOBILE_USER_AGENTS)
    
    def _get_headers(self):
        """Lấy headers chuẩn Pinterest theo response thật"""
        # Randomize một số headers để giống browser thật
        is_ios = "iPhone" in self.user_agent
        
        headers = {
            'accept': 'application/json, text/javascript, */*, q=0.01',
            'accept-language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.pinterest.com',
            'pragma': 'no-cache',
            'referer': 'https://www.pinterest.com/',
            'user-agent': self.user_agent,
            'x-csrftoken': self.csrftoken,
            'x-requested-with': 'XMLHttpRequest',
        }
        
        # Thêm mobile-specific headers
        if is_ios:
            headers.update({
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
            })
        else:
            # Android
            chrome_ver = random.randint(128, 132)
            headers.update({
                'sec-ch-ua': f'"Chromium";v="{chrome_ver}", "Not A(Brand";v="24"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
            })
        
        # Thêm Pinterest-specific headers từ response thật
        headers['x-app-version'] = '51c46db'
        headers['x-pinterest-appstate'] = random.choice(['active', 'background'])
        
        return headers
    
    def check_user_exists(self, username):
        """
        Kiểm tra user có tồn tại không bằng cách GET profile page
        Return: (exists: bool, message: str)
        """
        try:
            url = f'https://www.pinterest.com/{username}/'
            headers = {
                'user-agent': self.user_agent,
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = self.session.get(url, headers=headers, timeout=10, allow_redirects=True)
            
            # Check redirect về trang lỗi
            if 'show_error=true' in response.url:
                return False, "User không tồn tại (redirect error)"
            
            # Check 404
            if response.status_code == 404:
                return False, "User không tồn tại (404)"
            
            # Check 200 OK
            if response.status_code == 200:
                # Check nếu có content về user
                if username.lower() in response.text.lower():
                    return True, "User tồn tại"
                else:
                    return False, "User không tồn tại (no content)"
            
            return False, f"HTTP {response.status_code}"
            
        except Exception as e:
            # Nếu lỗi network, coi như user có thể tồn tại (để thử follow)
            return True, f"Không check được (error: {str(e)[:30]})"
    
    def like_pin(self, pin_id):
        """
        Like một pin trên Pinterest
        Endpoint: ReactionsResource/update/ (reaction_type: 1)
        """
        url = 'https://www.pinterest.com/resource/ReactionsResource/update/'
        
        headers = self._get_headers()
        
        # Payload theo format Pinterest thật
        payload = {
            'source_url': '/',
            'data': json.dumps({
                "options": {
                    "pin_id": str(pin_id),
                    "reaction_type": 1,  # 1 = like/heart
                    "client_tracking_params": ""
                },
                "context": {}
            })
        }
        
        # Retry logic: 3 lần
        for attempt in range(3):
            try:
                response = self.session.post(
                    url, 
                    headers=headers, 
                    data=payload, 
                    timeout=20,
                    allow_redirects=False
                )
                
                # Xử lý redirect error
                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get('Location', '')
                    if 'show_error=true' in location:
                        return False, "Pin không tồn tại (redirect)"
                
                # Success case
                if response.status_code == 200:
                    try:
                        data = response.json()
                        resource_response = data.get('resource_response', {})
                        
                        # Check success theo response thật
                        # endpoint_name: "v3_add_reaction_to_pin"
                        if resource_response.get('status') == 'success' and resource_response.get('code') == 0:
                            return True, "Like pin thành công"
                        
                        # Pin không tồn tại
                        elif resource_response.get('code') == 400:
                            return False, "Pin không tồn tại (code 400)"
                        
                        # Lỗi khác
                        else:
                            error_msg = resource_response.get('message', 'Unknown error')
                            return False, f"API error: {error_msg}"
                    
                    except json.JSONDecodeError:
                        return False, "Invalid JSON response"
                
                # 404 = Pin không tồn tại
                elif response.status_code == 404:
                    return False, "Pin không tồn tại (404)"
                
                # Rate limit
                elif response.status_code == 429:
                    if attempt < 2:
                        wait_time = (attempt + 1) * 30
                        time.sleep(wait_time)
                        continue
                    return False, "Rate limit exceeded"
                
                # Session hết hạn
                elif response.status_code in [403, 401]:
                    return False, "Session hết hạn - cần đổi cookies"
                
                # Lỗi khác
                else:
                    if attempt < 2:
                        time.sleep(3)
                        continue
                    return False, f"HTTP {response.status_code}"
            
            except requests.exceptions.Timeout:
                if attempt < 2:
                    time.sleep(5)
                    continue
                return False, "Request timeout"
            
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(3)
                    continue
                return False, f"Network error: {str(e)[:40]}"
            
            except Exception as e:
                if attempt < 2:
                    time.sleep(3)
                    continue
                return False, f"Error: {str(e)[:50]}"
        
        return False, "Failed after 3 attempts"
    
    def follow_user(self, user_id, link=None):
        """
        Follow user trên Pinterest
        Theo đúng format response thật từ tài liệu
        """
        url = 'https://www.pinterest.com/resource/UserFollowResource/create/'
        
        headers = self._get_headers()
        
        # Payload theo format Pinterest thật
        payload = {
            'source_url': '/',
            'data': json.dumps({
                "options": {
                    "user_id": str(user_id),
                },
                "context": {}
            })
        }
        
        # Retry logic: 3 lần
        for attempt in range(3):
            try:
                response = self.session.post(
                    url, 
                    headers=headers, 
                    data=payload, 
                    timeout=20,
                    allow_redirects=False
                )
                
                # Xử lý redirect error
                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get('Location', '')
                    if 'show_error=true' in location:
                        return False, "User không tồn tại (redirect)"
                
                # Success case
                if response.status_code == 200:
                    try:
                        data = response.json()
                        resource_response = data.get('resource_response', {})
                        
                        # Check success theo response thật
                        if resource_response.get('status') == 'success' and resource_response.get('code') == 0:
                            username = resource_response.get('data', {}).get('username', 'unknown')
                            return True, f"Follow {username} thành công"
                        
                        # User không tồn tại
                        elif resource_response.get('code') == 400:
                            return False, "User không tồn tại (code 400)"
                        
                        # Lỗi khác
                        else:
                            error_msg = resource_response.get('message', 'Unknown error')
                            return False, f"API error: {error_msg}"
                    
                    except json.JSONDecodeError:
                        return False, "Invalid JSON response"
                
                # 404 = User không tồn tại
                elif response.status_code == 404:
                    return False, "User không tồn tại (404)"
                
                # Rate limit
                elif response.status_code == 429:
                    if attempt < 2:
                        wait_time = (attempt + 1) * 30
                        time.sleep(wait_time)
                        continue
                    return False, "Rate limit exceeded"
                
                # Session hết hạn
                elif response.status_code in [403, 401]:
                    return False, "Session hết hạn - cần đổi cookies"
                
                # Lỗi khác
                else:
                    if attempt < 2:
                        time.sleep(3)
                        continue
                    return False, f"HTTP {response.status_code}"
            
            except requests.exceptions.Timeout:
                if attempt < 2:
                    time.sleep(5)
                    continue
                return False, "Request timeout"
            
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(3)
                    continue
                return False, f"Network error: {str(e)[:40]}"
            
            except Exception as e:
                if attempt < 2:
                    time.sleep(3)
                    continue
                return False, f"Error: {str(e)[:50]}"
        
        return False, "Failed after 3 attempts"
    
    def check_session(self):
        """Kiểm tra session còn hoạt động không"""
        try:
            url = 'https://www.pinterest.com/'
            headers = {
                'user-agent': self.user_agent,
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            response = self.session.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            # Check nếu bị redirect về login
            if 'login' in response.url.lower():
                return False
            
            # Check status code
            if response.status_code == 200:
                return True
            
            # Các status code khác vẫn coi như OK (có thể do rate limit tạm thời)
            # Chỉ fail khi chắc chắn redirect về login
            return response.status_code < 500
            
        except Exception as e:
            # Nếu lỗi network, coi như session vẫn OK (không vội kết luận)
            return True

# ==================== GOLIKE API ====================
def get_golike_headers():
    """Headers cho GoLike API - MOBILE ONLY với fake UA theo ig.py"""
    # Random mobile UA
    ua = random.choice(MOBILE_USER_AGENTS)
    is_ios = "iPhone" in ua
    
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

class GoLike:
    """GoLike API handler - sử dụng TLS client"""
    
    def __init__(self, auth, session):
        self.auth = auth
        self.s = session
    
    def _req(self, method, ep, data=None):
        """Make request đến GoLike API"""
        headers = get_golike_headers()  # Dùng mobile headers
        
        # Xử lý auth - tự động thêm Bearer nếu chưa có
        auth = self.auth.strip()
        if not auth.lower().startswith('bearer '):
            auth = f"Bearer {auth}"
        headers["authorization"] = auth
        
        url = f"{GOLIKE_BASE_URL}{ep}"
        
        # Retry 3 lần
        for attempt in range(3):
            try:
                if method.upper() == "GET":
                    r = self.s.get(url, headers=headers)
                else:
                    r = self.s.post(url, headers=headers, json=data)
                
                if not r or not hasattr(r, 'status_code'):
                    time.sleep(2)
                    continue
                
                try:
                    return r.json()
                except:
                    time.sleep(2)
                    continue
                    
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                    continue
                write_log(f"GoLike API error: {e}")
                return None
        
        return None
    
    def me(self):
        """Lấy thông tin user"""
        return self._req("GET", "/users/me")
    
    def accounts(self):
        """Lấy danh sách accounts Pinterest"""
        return self._req("GET", "/pinterest-account")
    
    def jobs(self, aid):
        """Lấy job mới"""
        return self._req("GET", f"/advertising/publishers/pinterest/jobs?account_id={aid}")
    
    def skip(self, aid, job_id):
        """Skip job"""
        data = {
            "account_id": str(aid),
            "ads_id": str(job_id)
        }
        return self._req("POST", "/advertising/publishers/pinterest/skip-jobs", data)
    
    def complete(self, aid, job_id, object_id):
        """Complete job - báo cáo thành công"""
        data = {
            "account_id": str(aid),
            "ads_id": str(job_id),
            "object_id": str(object_id)
        }
        return self._req("POST", "/advertising/publishers/pinterest/complete-jobs", data)
    
    def get_logs(self, aid, log_type="pending", page=1):
        """Lấy lịch sử jobs (pending/paid)"""
        return self._req("GET", f"/advertising/publishers/pinterest/logs?account_id={aid}&log_type={log_type}&page={page}")

# ==================== WORKER ====================
class Worker:
    """Worker xử lý job cho 1 account"""
    
    _permanently_stopped = set()  # Class variable lưu các account đã dừng vĩnh viễn
    
    def __init__(self, golike, acc, cookies, stats, auto_mode, min_delay, max_delay, max_fails):
        self.gl = golike
        self.acc = acc
        self.aid = str(acc.get("id"))  # Response dùng "id"
        self.name = acc.get("username") or self.aid
        self.pinterest_username = acc.get("pinterest_username", "N/A")
        self.stats = stats
        self.auto = auto_mode
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_fails = max_fails
        
        # Pinterest API - validate cookies ngay
        try:
            self.pin = PinterestAPI(cookies)
        except ValueError as e:
            print_log(self.name, str(e), "fail")
            print_log(self.name, "💡 Hãy lấy cookies đầy đủ từ pinterest.com", "warn")
            raise
        
        # State
        self.running = True
        self.consecutive_fails = 0
        self.total_jobs_done = 0
        self.total_money_earned = 0
        
        # Auto refresh cookies config
        self.jobs_since_last_check = 0
        self.check_session_every = 10  # Check session mỗi 10 jobs
        
        # Track job retries để tránh retry vô hạn
        self.job_retry_count = {}  # {job_id: retry_count}
        self.max_retries_per_job = 2  # Retry 2 lần, lần 3 complete ảo
        self.skipped_jobs = set()  # Track các job đã skip để không nhận lại
        self.max_skipped_jobs = 100  # Giới hạn số job lưu trong skipped_jobs
    
    def _update_stats(self, success):
        """Update statistics thread-safe"""
        with stats_lock:
            if success:
                self.stats.ok += 1
            else:
                self.stats.fail += 1
    
    def _handle_job(self, job_data):
        """
        Xử lý 1 job
        Returns: (success: bool, should_continue: bool, message: str)
        """
        job_id = job_data.get("id")
        object_id = job_data.get("object_id")
        link = job_data.get("link", "")
        price = job_data.get("price_after_cost", 0)
        job_type = job_data.get("type", "follow")
        
        username = extract_username_from_link(link)
        display_name = username or object_id
        
        # CHECK NẾU JOB ĐÃ SKIP - Gọi skip API và bỏ qua
        if job_id in self.skipped_jobs:
            print_log(self.name, f"⊘ Job #{job_id} đã skip - gọi skip API lại", "skip")
            
            # Gọi skip API để đảm bảo GoLike biết
            skip_resp = self.gl.skip(self.aid, job_id)
            if skip_resp and skip_resp.get("success"):
                print_log(self.name, "⊘ Skip API thành công", "skip")
            
            # Delay ngắn để tránh nhận lại job này ngay
            time.sleep(1)
            
            return False, True, "Already skipped"
        
        # Clear skipped_jobs nếu quá nhiều (giữ 100 job gần nhất)
        if len(self.skipped_jobs) > self.max_skipped_jobs:
            # Convert to list, remove oldest half
            skipped_list = list(self.skipped_jobs)
            self.skipped_jobs = set(skipped_list[-self.max_skipped_jobs//2:])
            print_log(self.name, "🧹 Đã dọn dẹp danh sách job đã skip", "info")
        
        # CHECK RETRY COUNT - Complete ảo nếu đã retry quá nhiều lần
        retry_count = self.job_retry_count.get(job_id, 0)
        if retry_count >= self.max_retries_per_job:
            print_log(self.name, f"⚠️  Job #{job_id} đã retry {retry_count} lần - Dùng khổ nhục kế!", "warn")
            
            # Thêm vào danh sách đã skip TRƯỚC để tránh loop
            self.skipped_jobs.add(job_id)
            
            # Reset retry count
            if job_id in self.job_retry_count:
                del self.job_retry_count[job_id]
            
            # Complete ảo để qua job mới (không thực sự follow/like)
            complete_resp = self.gl.complete(self.aid, job_id, object_id)
            
            if complete_resp and complete_resp.get("success"):
                print_log(self.name, f"✓ Complete ảo OK → +{price}đ", "complete")
                
                # Tính vào stats như job thành công
                self.total_jobs_done += 1
                self.total_money_earned += price
                self._update_stats(True)
                self.consecutive_fails = 0
                
                # Delay để tránh spam
                time.sleep(2)
                
                return True, True, "Fake complete success"
            else:
                # Nếu complete fail (job đã hết hạn/xóa), thử skip
                print_log(self.name, "⚠ Complete ảo fail - job có thể đã hết hạn", "warn")
                
                skip_resp = self.gl.skip(self.aid, job_id)
                if skip_resp and skip_resp.get("success"):
                    print_log(self.name, "⊘ Skip thành công", "skip")
                
                self._update_stats(False)
                self.consecutive_fails = 0
                
                # Delay
                time.sleep(1)
                
                return False, True, "Job expired or already completed"
        
        print_log(self.name, f"Job #{job_id}: {job_type} → {display_name} ({price}đ)", "info")
        
        # CHECK USER TỒN TẠI CHỈ ÁP DỤNG CHO FOLLOW
        if job_type == "follow" and username:
            print_log(self.name, f"🔍 Đang check user: {username}...", "info")
            exists, check_msg = self.pin.check_user_exists(username)
            
            if not exists:
                print_log(self.name, f"⊘ {check_msg} - Skip job!", "skip")
                
                # Skip job trên GoLike
                skip_resp = self.gl.skip(self.aid, job_id)
                if skip_resp and skip_resp.get("success"):
                    print_log(self.name, "⊘ Đã skip job trên GoLike", "skip")
                
                # Thêm vào danh sách đã skip
                self.skipped_jobs.add(job_id)
                
                self._update_stats(False)
                self.consecutive_fails = 0  # Không tính fail vì user không tồn tại
                return False, True, check_msg
            else:
                print_log(self.name, f"✓ {check_msg}", "info")
        
        # Xử lý job theo type
        if job_type == "follow":
            success, msg = self.pin.follow_user(object_id, link)
        elif job_type == "like":
            success, msg = self.pin.like_pin(object_id)
        else:
            # Unsupported job type
            print_log(self.name, f"⊘ Job type '{job_type}' chưa được hỗ trợ - Skip!", "skip")
            skip_resp = self.gl.skip(self.aid, job_id)
            if skip_resp and skip_resp.get("success"):
                print_log(self.name, "⊘ Đã skip job", "skip")
            
            # Thêm vào danh sách đã skip
            self.skipped_jobs.add(job_id)
            
            self._update_stats(False)
            return False, True, f"Unsupported type: {job_type}"
        
        if success:
            # Complete job
            complete_resp = self.gl.complete(self.aid, job_id, object_id)
            
            if complete_resp and complete_resp.get("success"):
                self.total_jobs_done += 1
                self.total_money_earned += price
                
                # Clear retry count cho job này (nếu có)
                if job_id in self.job_retry_count:
                    del self.job_retry_count[job_id]
                
                action_name = "Follow" if job_type == "follow" else "Like"
                print_log(
                    self.name, 
                    f"✓ {action_name} thành công | +{price}đ | Total: {self.total_jobs_done} jobs, {self.total_money_earned:,}đ", 
                    "success"
                )
                
                self._update_stats(True)
                self.consecutive_fails = 0
                return True, True, msg
            else:
                # Check nếu job đã bị xóa hoặc hết hạn (422)
                if complete_resp and complete_resp.get("status") == 422:
                    error_msg = complete_resp.get("message", "Job hết hạn")
                    print_log(self.name, f"⊘ {error_msg} - Lấy job mới", "warn")
                    
                    # Không tính fail, lấy job tiếp
                    self.consecutive_fails = 0
                    return False, True, "Job expired - continue"
                
                error_msg = complete_resp.get("message", "Unknown") if complete_resp else "No response"
                print_log(self.name, f"✗ Complete failed: {error_msg}", "fail")
                self._update_stats(False)
                return False, True, error_msg
        
        else:
            # Check nếu object không tồn tại → skip ngay
            if any(x in msg.lower() for x in ["không tồn tại", "404", "400", "redirect"]):
                print_log(self.name, f"⊘ Skip: {msg}", "skip")
                
                skip_resp = self.gl.skip(self.aid, job_id)
                if skip_resp and skip_resp.get("success"):
                    print_log(self.name, "⊘ Đã skip job", "skip")
                
                # Thêm vào danh sách đã skip
                self.skipped_jobs.add(job_id)
                
                self._update_stats(False)
                self.consecutive_fails = 0  # Reset vì không phải lỗi thật sự
                
                # Clear retry count
                if job_id in self.job_retry_count:
                    del self.job_retry_count[job_id]
                
                return False, True, msg
            
            # Lỗi session/authorization - cần kiểm tra kỹ
            elif "session" in msg.lower() or "401" in msg or "403" in msg:
                print_log(self.name, f"✗ {msg}", "fail")
                
                # Tăng retry count cho job này TRƯỚC KHI kiểm tra session
                current_retries = self.job_retry_count.get(job_id, 0)
                self.job_retry_count[job_id] = current_retries + 1
                
                print_log(self.name, f"📊 Job #{job_id} thất bại lần {self.job_retry_count[job_id]}/{self.max_retries_per_job} (lần sau sẽ complete ảo)", "info")
                
                # Nếu chưa đến ngưỡng retry, kiểm tra session
                if self.job_retry_count[job_id] < self.max_retries_per_job:
                    print_log(self.name, "🔍 Đang verify session...", "info")
                    if self.pin.check_session():
                        # Session vẫn OK - có thể là lỗi tạm thời hoặc job khó
                        print_log(self.name, "✓ Session vẫn OK - sẽ retry job này", "warn")
                        self._update_stats(False)
                        self.consecutive_fails = 0  # Không tính fail liên tiếp vì session OK
                        return False, True, "Temporary error - will retry"
                
                # Đã retry đủ 2 lần hoặc session không OK
                if self.job_retry_count[job_id] >= self.max_retries_per_job:
                    print_log(self.name, f"⚠️  Job #{job_id} đã thất bại {self.max_retries_per_job} lần", "warn")
                    
                    # Thêm vào skipped_jobs TRƯỚC
                    self.skipped_jobs.add(job_id)
                    
                    # Clear retry count
                    if job_id in self.job_retry_count:
                        del self.job_retry_count[job_id]
                    
                    # Kiểm tra session một lần nữa
                    print_log(self.name, "🔍 Kiểm tra session...", "check")
                    if self.pin.check_session():
                        # Session vẫn OK - dùng khổ nhục kế: complete ảo
                        print_log(self.name, "✓ Session OK - Complete ảo", "warn")
                        
                        # Complete ảo
                        complete_resp = self.gl.complete(self.aid, job_id, object_id)
                        
                        if complete_resp and complete_resp.get("success"):
                            self.total_jobs_done += 1
                            self.total_money_earned += price
                            print_log(self.name, f"✓ +{price}đ | Total: {self.total_jobs_done} jobs, {self.total_money_earned:,}đ", "money")
                            
                            self._update_stats(True)
                            self.consecutive_fails = 0
                            
                            # Delay
                            time.sleep(2)
                            
                            return True, True, "Fake complete success"
                        else:
                            # Complete fail → skip
                            print_log(self.name, "⚠ Complete fail - job đã hết hạn", "warn")
                            
                            skip_resp = self.gl.skip(self.aid, job_id)
                            if skip_resp and skip_resp.get("success"):
                                print_log(self.name, "⊘ Skip OK", "skip")
                            
                            self._update_stats(False)
                            self.consecutive_fails = 0
                            
                            time.sleep(1)
                            
                            return False, True, "Job expired"
                
                # Session thật sự hết hạn
                print_log(self.name, "🔄 Cookies Pinterest đã hết hạn!", "warn")
                
                # Yêu cầu nhập lại cookies
                print(f"\n{Fore.YELLOW}{'='*70}")
                print(f"⚠️  ACCOUNT {self.name} CẦN COOKIES MỚI")
                print('='*70 + Style.RESET_ALL)
                
                # Xóa cookies cũ
                delete_ck(self.aid)
                
                # Yêu cầu cookies mới
                new_ck = request_new_cookies(self.aid, self.name, self.pinterest_username)
                
                if new_ck:
                    # Thử tạo lại Pinterest API với cookies mới
                    try:
                        self.pin = PinterestAPI(new_ck)
                        if self.pin.check_session():
                            print_log(self.name, "✅ Cookies mới hợp lệ! Tiếp tục chạy...", "success")
                            self.consecutive_fails = 0  # Reset fail count
                            
                            # Clear retry count
                            if job_id in self.job_retry_count:
                                del self.job_retry_count[job_id]
                            
                            self._update_stats(False)
                            return False, True, "Đã đổi cookies mới"  # Continue
                        else:
                            print_log(self.name, "❌ Cookies mới vẫn không hợp lệ!", "fail")
                    except Exception as e:
                        print_log(self.name, f"❌ Lỗi validate cookies: {e}", "fail")
                
                # Không có cookies mới hoặc cookies mới không hợp lệ
                print_log(self.name, "⏹ Dừng worker - không có cookies hợp lệ", "fail")
                self._update_stats(False)
                return False, False, msg
            
            # Lỗi khác (network, rate limit, etc.)
            else:
                print_log(self.name, f"✗ {msg}", "fail")
                
                # Tăng retry count cho job này
                current_retries = self.job_retry_count.get(job_id, 0)
                self.job_retry_count[job_id] = current_retries + 1
                
                print_log(self.name, f"📊 Job #{job_id} thất bại lần {self.job_retry_count[job_id]}/{self.max_retries_per_job} (lần sau sẽ complete ảo)", "info")
                
                self._update_stats(False)
                
                # Nếu đã retry đủ lần, logic complete ảo sẽ xử lý ở đầu hàm
                if self.job_retry_count[job_id] >= self.max_retries_per_job:
                    print_log(self.name, f"⚠️  Job #{job_id} thất bại {self.max_retries_per_job} lần - lần sau complete ảo", "warn")
                    self.consecutive_fails = 0  # Không tính fail liên tiếp
                else:
                    self.consecutive_fails += 1
                
                return False, True, msg
    
    def run(self):
        """Main loop của worker"""
        
        # Check session trước
        if not self.pin.check_session():
            print_log(self.name, "❌ Session không hợp lệ - kiểm tra lại cookies!", "fail")
            return
        
        print_log(self.name, f"🚀 Bắt đầu chạy (Mode: {'AUTO' if self.auto else 'MANUAL'})", "info")
        
        no_job_count = 0
        
        while self.running and self.aid not in Worker._permanently_stopped:
            try:
                # Check consecutive fails
                if self.consecutive_fails >= self.max_fails:
                    print_log(
                        self.name, 
                        f"⏹ Dừng do {self.consecutive_fails} lần thất bại liên tiếp", 
                        "warn"
                    )
                    Worker._permanently_stopped.add(self.aid)
                    break
                
                # Lấy job
                job_resp = self.gl.jobs(self.aid)
                
                if not job_resp:
                    print_log(self.name, "❌ Không lấy được job từ GoLike", "fail")
                    time.sleep(ERROR_RETRY_TIME)
                    continue
                
                # Check error
                if not job_resp.get("success"):
                    error_msg = job_resp.get("message", "Unknown error")
                    
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
                        
                        # Countdown với progress bar
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
                                mins = i // 60
                                secs = i % 60
                                sys.stdout.write(f"\r{Fore.YELLOW}[{self.name}] 💤 Chờ: {mins}m {secs}s {Style.RESET_ALL}")
                                sys.stdout.flush()
                                time.sleep(1)
                                if not self.running:
                                    break
                            sys.stdout.write("\r" + " " * 80 + "\r")
                            sys.stdout.flush()
                        
                        print_log(self.name, f"✅ Đã nghỉ xong {mins} phút - Tiếp tục check job!", "info")
                        continue
                    
                    # Lỗi khác
                    print_log(self.name, f"❌ GoLike error: {error_msg}", "fail")
                    time.sleep(ERROR_RETRY_TIME)
                    continue
                
                # Lấy job data
                job_data = job_resp.get("data")
                
                if not job_data:
                    no_job_count += 1
                    print_log(self.name, f"⏸ Hết việc (lần {no_job_count})", "warn")
                    
                    if no_job_count >= 3:
                        print_log(self.name, f"⏹ Dừng vĩnh viễn - hết việc", "warn")
                        Worker._permanently_stopped.add(self.aid)
                        break
                    
                    wait_time = NO_JOB_WAIT_TIME
                    print_log(self.name, f"⏳ Chờ {wait_time//60} phút để kiểm tra lại...", "info")
                    
                    # Countdown với progress bar
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
                            transient=False  # Giữ lại để thấy progress
                        ) as progress:
                            task = progress.add_task(
                                f"[{self.name}] 💤 Chờ job mới", 
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
                            mins = i // 60
                            secs = i % 60
                            sys.stdout.write(f"\r{Fore.YELLOW}[{self.name}] 💤 Chờ: {mins}m {secs}s {Style.RESET_ALL}")
                            sys.stdout.flush()
                            time.sleep(1)
                            if not self.running:
                                break
                        sys.stdout.write("\r" + " " * 80 + "\r")
                        sys.stdout.flush()
                    
                    continue
                
                # Reset no_job_count khi có job
                no_job_count = 0
                
                # CHECK SESSION định kỳ (mỗi 10 jobs)
                self.jobs_since_last_check += 1
                if self.jobs_since_last_check >= self.check_session_every:
                    print_log(self.name, "🔍 Checking session...", "info")
                    if not self.pin.check_session():
                        print_log(self.name, "⚠️  Session có vẻ yếu - cần refresh cookies sớm!", "warn")
                    self.jobs_since_last_check = 0
                
                # CHECK LOCK TIME - Nếu lock_time quá ngắn thì skip ngay
                lock_info = job_resp.get("lock")
                if lock_info:
                    lock_time = int(lock_info.get("lock_time", 600))
                    if lock_time < 60:  # Nếu còn dưới 1 phút thì skip
                        print_log(self.name, f"⊘ Job sắp hết hạn (còn {lock_time}s) - Skip!", "warn")
                        job_id = job_data.get("id")
                        self.gl.skip(self.aid, job_id)
                        time.sleep(1)
                        continue
                
                # Xử lý job
                success, should_continue, msg = self._handle_job(job_data)
                
                if not should_continue:
                    print_log(self.name, "⏹ Dừng worker do lỗi nghiêm trọng", "warn")
                    break
                
                # Delay với countdown animation
                if self.running:
                    delay = random.uniform(self.min_delay, self.max_delay)
                    
                    # Hiển thị countdown với animation
                    if HAS_RICH:
                        # Sử dụng Rich Progress Bar
                        from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
                        
                        with Progress(
                            SpinnerColumn(),
                            TextColumn("[cyan]{task.description}"),
                            BarColumn(bar_width=30),
                            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                            TextColumn("•"),
                            TimeRemainingColumn(),
                            console=console,
                            transient=True  # Tự động xóa sau khi xong
                        ) as progress:
                            task = progress.add_task(
                                f"[{self.name}] ⏳ Chờ", 
                                total=int(delay * 10)
                            )
                            
                            for i in range(int(delay * 10)):
                                time.sleep(0.1)
                                progress.update(task, advance=1)
                                if not self.running:
                                    break
                    else:
                        # Fallback: Countdown text với animation
                        import sys
                        remaining = delay
                        while remaining > 0 and self.running:
                            mins = int(remaining // 60)
                            secs = int(remaining % 60)
                            
                            if mins > 0:
                                time_str = f"{mins}m {secs}s"
                            else:
                                time_str = f"{secs}s"
                            
                            # Animation với các ký tự khác nhau
                            spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                            spinner = spinner_chars[int(remaining * 2) % len(spinner_chars)]
                            
                            sys.stdout.write(f"\r{Fore.CYAN}[{self.name}] {spinner} Chờ: {time_str} {Style.RESET_ALL}")
                            sys.stdout.flush()
                            
                            sleep_time = min(0.5, remaining)
                            time.sleep(sleep_time)
                            remaining -= sleep_time
                        
                        # Clear dòng countdown
                        sys.stdout.write("\r" + " " * 80 + "\r")
                        sys.stdout.flush()
            
            except KeyboardInterrupt:
                print_log(self.name, "⏸ Nhận lệnh dừng", "warn")
                break
            
            except Exception as e:
                print_log(self.name, f"❌ Lỗi không xác định: {str(e)[:80]}", "fail")
                time.sleep(5)
        
        print_log(
            self.name, 
            f"⏹ Đã dừng | Hoàn thành: {self.total_jobs_done} jobs, {self.total_money_earned:,}đ", 
            "info"
        )
        
        # Hiển thị summary ngắn
        if self.total_jobs_done > 0:
            avg_money_per_job = self.total_money_earned / self.total_jobs_done if self.total_jobs_done > 0 else 0
            print_log(
                self.name,
                f"📊 Trung bình: {avg_money_per_job:.0f}đ/job",
                "info"
            )

# ==================== STATS ====================
class Stats:
    """Statistics tracker"""
    def __init__(self):
        self.ok = 0
        self.fail = 0

# ==================== GUI ====================
def show_banner():
    """Hiển thị banner với hiệu ứng đẹp"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    if HAS_RICH:
        from rich.align import Align
        from rich.panel import Panel
        from rich.text import Text
        
        # ASCII Art với gradient
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║  ██████╗ ██╗███╗   ██╗████████╗███████╗██████╗ ███████╗███████╗████████╗ ║
║  ██╔══██╗██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝ ║
║  ██████╔╝██║██╔██╗ ██║   ██║   █████╗  ██████╔╝█████╗  ███████╗   ██║    ║
║  ██╔═══╝ ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗██╔══╝  ╚════██║   ██║    ║
║  ██║     ██║██║ ╚████║   ██║   ███████╗██║  ██║███████╗███████║   ██║    ║
║  ╚═╝     ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝    ║
╚═══════════════════════════════════════════════════════════════╝
        """
        
        # Tạo text với gradient màu
        title_text = Text()
        colors = ["magenta", "bright_magenta", "bright_blue", "cyan"]
        lines = banner.strip().split('\n')
        
        for i, line in enumerate(lines):
            color_idx = i % len(colors)
            title_text.append(line + "\n", style=colors[color_idx])
        
        console.print(Align.center(title_text))
        
        # Info panel với icons
        info = Text()
        info.append("🎨 ", style="bold magenta")
        info.append("AUTO GOLIKE TOOL", style="bold bright_cyan")
        info.append(" v3.0 ULTIMATE\n", style="bold yellow")
        
        info.append("\n")
        info.append("⚡ ", style="bold yellow")
        info.append("Features: ", style="bold white")
        info.append("Follow • Like • Smart Retry • Fake Complete\n", style="cyan")
        
        info.append("🎯 ", style="bold green")
        info.append("Mode: ", style="bold white")
        info.append("Multi-threaded • Auto Skip • Session Check\n", style="green")
        
        info.append("💰 ", style="bold yellow")
        info.append("Profit: ", style="bold white")
        info.append("Real-time Stats • Money Counter • Job History", style="yellow")
        
        console.print(Panel(
            Align.center(info),
            border_style="bright_magenta",
            title="[bold yellow]⭐ PINTEREST AUTOMATION ⭐[/bold yellow]",
            subtitle="[italic cyan]Made with ❤️  by Expert[/italic cyan]",
            padding=(1, 4)
        ))
        
        # Separator với animation
        separator = Text("─" * 80, style="bright_blue")
        console.print(Align.center(separator))
        console.print()
        
    else:
        # Fallback cho terminal không hỗ trợ Rich
        print(Fore.MAGENTA + Style.BRIGHT + """
╔═══════════════════════════════════════════════════════════════╗
║  ██████╗ ██╗███╗   ██╗████████╗███████╗██████╗ ███████╗███████╗████████╗ ║
║  ██╔══██╗██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝ ║
║  ██████╔╝██║██╔██╗ ██║   ██║   █████╗  ██████╔╝█████╗  ███████╗   ██║    ║
║  ██╔═══╝ ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗██╔══╝  ╚════██║   ██║    ║
║  ██║     ██║██║ ╚████║   ██║   ███████╗██║  ██║███████╗███████║   ██║    ║
║  ╚═╝     ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝    ║
╚═══════════════════════════════════════════════════════════════╝
        """ + Style.RESET_ALL)
        
        print(Fore.CYAN + Style.BRIGHT + "🎨 AUTO GOLIKE TOOL v3.0 ULTIMATE")
        print(Fore.YELLOW + "⚡ Follow • Like • Smart Retry • Fake Complete")
        print(Style.RESET_ALL + "\n")

def prompt(msg, required=True, hidden=False):
    """Prompt với validation"""
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

def run_parallel(gl, accs, cks, cfg):
    """Chạy nhiều workers song song"""
    
    auto = cfg.get("auto_mode", True)
    min_d = cfg.get("min_delay", 5.0)
    max_d = cfg.get("max_delay", 10.0)
    max_f = cfg.get("max_fails", MAX_CONSECUTIVE_FAILS)
    
    num_workers = min(len(accs), MAX_WORKERS)
    
    stats = Stats()
    workers = []
    
    for acc in accs:
        aid = str(acc.get("id"))  # Response dùng "id"
        ck = cks.get(aid)
        
        if not ck:
            print(f"{Fore.RED}❌ Không có cookies cho account {aid}{Style.RESET_ALL}")
            continue
        
        try:
            worker = Worker(gl, acc, ck, stats, auto, min_d, max_d, max_f)
            workers.append(worker)
        except ValueError as e:
            # Lỗi cookies thiếu csrftoken
            username = acc.get("username", aid)
            print(f"\n{Fore.RED}❌ Account {username}: Cookies không hợp lệ!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 Hãy xóa file pinterest_ck_{aid}.txt và lấy lại cookies đầy đủ{Style.RESET_ALL}\n")
            continue
    
    if not workers:
        print(f"{Fore.RED}❌ Không có worker nào được tạo!{Style.RESET_ALL}")
        return
    
    print(f"{Fore.CYAN}🚀 Bắt đầu với {len(workers)} workers song song{Style.RESET_ALL}\n")
    
    try:
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker.run) for worker in workers]
            
            for future in futures:
                future.result()
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⏸ Đang dừng tất cả workers...{Style.RESET_ALL}")
        
        for worker in workers:
            worker.running = False
        
        time.sleep(2)
    
    # Kết quả cuối cùng
    print(f"\n{Fore.CYAN}{'='*60}")
    print("📊 KẾT QUẢ CUỐI CÙNG")
    print('='*60 + Style.RESET_ALL)
    
    if Worker._permanently_stopped:
        print(f"\n{Fore.RED}⏹ CÁC ACCOUNT ĐÃ DỪNG VĨNH VIỄN:{Style.RESET_ALL}")
        for aid in Worker._permanently_stopped:
            acc_name = aid
            for w in workers:
                if w.aid == aid:
                    acc_name = w.name
                    break
            print(f"  • {acc_name} (ID: {aid})")
        print()
    
    # Tổng hợp từ workers
    total_jobs = sum(w.total_jobs_done for w in workers)
    total_money = sum(w.total_money_earned for w in workers)
    
    total = stats.ok + stats.fail
    rate = (stats.ok / total * 100) if total > 0 else 0
    
    print(f"{Fore.GREEN}✓ THÀNH CÔNG: {stats.ok}")
    print(f"{Fore.RED}✗ THẤT BẠI: {stats.fail}")
    print(f"{Fore.CYAN}TỶ LỆ: {rate:.1f}%")
    print(f"{Fore.YELLOW}💼 TỔNG JOBS: {total_jobs}")
    print(f"{Fore.GREEN}💰 TỔNG TIỀN: {total_money:,}đ")
    
    if total_jobs > 0:
        print(f"{Fore.MAGENTA}📊 TRUNG BÌNH: {total_money/total_jobs:.0f}đ/job")
    
    print('='*60 + Style.RESET_ALL + "\n")

def show_account_logs(gl, acc):
    """Hiển thị lịch sử jobs của account"""
    aid = str(acc.get("id"))
    username = acc.get("username", aid)
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"📋 LỊCH SỬ JOBS - ACCOUNT: {username}")
    print('='*70 + Style.RESET_ALL)
    
    # Lấy logs pending (chưa thanh toán)
    logs_resp = gl.get_logs(aid, log_type="pending", page=1)
    
    if not logs_resp or not logs_resp.get("success"):
        print(f"{Fore.RED}❌ Không lấy được logs!{Style.RESET_ALL}")
        return
    
    logs = logs_resp.get("data", [])
    
    if not logs:
        print(f"{Fore.YELLOW}⚠️  Chưa có job nào!{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}✓ Tìm thấy {len(logs)} jobs chờ thanh toán{Style.RESET_ALL}\n")
    
    # Hiển thị table
    if HAS_RICH:
        table = Table(title=f"Jobs Pending - {username}", border_style="cyan")
        table.add_column("ID", style="yellow", width=8)
        table.add_column("Type", style="magenta", width=8)
        table.add_column("Object", style="cyan", width=30)
        table.add_column("Price", style="green", width=10)
        table.add_column("Time", style="white", width=20)
        
        total_pending = 0
        for log in logs[:20]:  # Chỉ hiển thị 20 đầu
            job_id = str(log.get("id"))
            job_type = log.get("type", "?")
            link = log.get("link", "")
            price = log.get("prices", 0)
            created = log.get("created_at", "")
            
            # Extract display name
            if "pinterest.com/pin/" in link:
                obj_name = "pin/" + link.split("/pin/")[1][:15] + "..."
            elif "pinterest.com/" in link:
                obj_name = link.split("pinterest.com/")[1][:30]
            else:
                obj_name = link[:30]
            
            table.add_row(job_id, job_type, obj_name, f"{price}đ", created.split(" ")[1] if " " in created else created)
            total_pending += price
        
        console.print(table)
        
        if len(logs) > 20:
            print(f"\n{Fore.YELLOW}... và {len(logs)-20} jobs nữa{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}💰 TỔNG TIỀN CHỜ THANH TOÁN: {total_pending:,}đ{Style.RESET_ALL}")
    else:
        # Fallback without Rich
        total_pending = 0
        for i, log in enumerate(logs[:20], 1):
            job_id = log.get("id")
            job_type = log.get("type", "?")
            price = log.get("prices", 0)
            created = log.get("created_at", "")
            
            print(f"{Fore.YELLOW}[{i}]{Style.RESET_ALL} ID: {job_id} | Type: {job_type} | {price}đ | {created}")
            total_pending += price
        
        if len(logs) > 20:
            print(f"\n{Fore.YELLOW}... và {len(logs)-20} jobs nữa{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}💰 TỔNG: {total_pending:,}đ{Style.RESET_ALL}")
    
    print()

def main():
    """Main entry point"""
    show_banner()
    cfg = load_config()
    
    # Create TLS session cho GoLike với random TLS như ig.py
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
        print(Fore.RED + "❌ Không có tài khoản Pinterest nào trên GoLike!" + Style.RESET_ALL)
        return
    
    print(Fore.GREEN + f"✓ Tìm thấy {len(accs)} tài khoản Pinterest\n" + Style.RESET_ALL)
    
    # Option xem logs
    if prompt("📋 Xem lịch sử jobs trước? (y/n, mặc định n): ", required=False).lower() == 'y':
        for acc in accs:
            show_account_logs(gl, acc)
        
        if prompt("\n▶️  Tiếp tục chạy tool? (y/n): ", required=False).lower() != 'y':
            return
    
    # Hiển thị danh sách accounts
    if HAS_RICH:
        table = Table(title="📌 DANH SÁCH TÀI KHOẢN", border_style="magenta")
        table.add_column("Index", style="yellow", width=8)
        table.add_column("Username", style="cyan")
        table.add_column("Pinterest", style="green")
        table.add_column("ID", style="white")
        
        for i, a in enumerate(accs):
            aid = str(a.get("id"))  # Response dùng "id" không phải "account_id"
            username = a.get("username") or aid
            pinterest_username = a.get("pinterest_username", "N/A")
            table.add_row(str(i), username, pinterest_username, aid)
        
        console.print(table)
    else:
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print("📌 DANH SÁCH TÀI KHOẢN")
        print('='*60 + Style.RESET_ALL)
        for i, a in enumerate(accs):
            aid = str(a.get("id"))
            username = a.get("username") or aid
            pinterest_username = a.get("pinterest_username", "N/A")
            print(f"{Fore.YELLOW}[{i}]{Style.RESET_ALL} {Fore.CYAN}{username}{Style.RESET_ALL} (@{pinterest_username}) - ID: {aid}")
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
        aid = str(a.get("id"))  # Response dùng "id"
        username = a.get("username") or aid
        pinterest_username = a.get("pinterest_username", "N/A")
        
        ck = load_ck(aid)
        
        # Nếu chưa có cookies hoặc cookies cũ
        while not ck or not parse_cookies(ck).get('csrftoken'):
            if ck and not parse_cookies(ck).get('csrftoken'):
                print(f"\n{Fore.RED}❌ Cookies cũ của {username} thiếu csrftoken!{Style.RESET_ALL}")
                delete_ck(aid)
            
            ck = request_new_cookies(aid, username, pinterest_username)
            
            if not ck:
                print(f"{Fore.YELLOW}⚠️  Bỏ qua account {username}{Style.RESET_ALL}")
                break
        
        if ck:
            cks[aid] = ck
    
    # Cài đặt
    print(f"\n{Fore.CYAN}{'='*60}")
    print("⚙️  CÀI ĐẶT")
    print('='*60 + Style.RESET_ALL)
    
    print(f"\n{Fore.YELLOW}💡 KHUYẾN NGHỊ (để tránh cookies hết hạn nhanh):{Style.RESET_ALL}")
    print(f"   • Delay min: 10-15s")
    print(f"   • Delay max: 20-30s")
    print(f"   • Chạy ổn định, tránh spam → Pinterest không phát hiện\n")
    
    auto = prompt("🎯 Chế độ (1=AUTO, 2=MANUAL, mặc định AUTO): ", required=False) != "2"
    
    min_input = prompt("⏱️  Delay min (giây, khuyến nghị 12): ", required=False) or "12"
    min_d = float(min_input)
    
    max_input = prompt("⏱️  Delay max (giây, khuyến nghị 25): ", required=False) or "25"
    max_d = float(max_input)
    
    # Warning nếu delay quá ngắn
    if min_d < 8:
        print(f"\n{Fore.RED}⚠️  CẢNH BÁO: Delay quá ngắn!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   → Cookies sẽ hết hạn nhanh vì Pinterest phát hiện spam")
        print(f"   → Khuyến nghị: min >= 10s{Style.RESET_ALL}")
        
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