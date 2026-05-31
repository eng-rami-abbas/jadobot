import requests
import time
import sys
import os
import json
from datetime import datetime

# أضف المسار للوصول إلى config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import config.telegram
    import handlers.ichancy
    COOKIE_STRING = config.telegram.COOKIE_STRING
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loaded cookie string")
except ImportError:
    print("ERROR: Cannot import config.telegram")
    COOKIE_STRING = "languageCode=ar_IQ; PHPSESSID_3a07edcde6f57a008f3251235df79776a424dd7623e40d4250e37e4f1f15fadf=f938e56fdee08c821e7a9907784d3a1e; __cf_bm=uNjPiNu9BlUl1.cv55hlPfy7X6epueX_DZ7RHSPRS8k-1767117041-1.0.1.1-1ghAemHHwh2v.dG6MBFY8ZGe4y3.7Ou1vKyWdVqAKD8S1lINy5wJyfFWV9RIZxWo9c9baMNgLjYKrvIqE.K4lcpB_hzX4n_uOUBJ_P9kt7c; cf_clearance=19tRP2YlZHyECGdVR.F18JmRNKntbtQy60R6OVLV2jk-1767117081-1.2.1.1-xRehKFLFfOw8YDpigmK6tGIvPN5jdaU4pGPEdXQqzlw_xbkM2OEntSPSjgwQysUU2fo4cRkZsukfohEuT3.yDOLf771u27vR40LySj26I_y.g1_Ixvb1JuW0l4oEeA4HbvQ_ka1tAK7ugkQNUTZPNK2xMs1P85ECWB60WvL1S5K_1Ko.s.j_AsKkqFAl8VG1iLMyw67SpcQndfGAvrZcG82qQWKuRDNroK3wNPGiXss"

class SessionKeeper:
    def __init__(self):
        self.session = requests.Session()
        self.cookies = self.parse_cookies(COOKIE_STRING)
        self.last_refresh = time.time()
        self.refresh_interval = 20 * 60  # 20 دقيقة
        self.failed_attempts = 0
        
        # تحديث جلسة requests بالكوكيز
        for name, value in self.cookies.items():
            self.session.cookies.set(name, value)
        
        print(f"[{self.timestamp()}] Session initialized with {len(self.cookies)} cookies")
    
    def timestamp(self):
        return datetime.now().strftime('%H:%M:%S')
    
    def parse_cookies(self, cookie_string):
        """تحويل سلسلة الكوكيز إلى dictionary"""
        cookies = {}
        if not cookie_string:
            return cookies
            
        cookie_pairs = cookie_string.split(';')
        for pair in cookie_pairs:
            pair = pair.strip()
            if '=' in pair:
                name, value = pair.split('=', 1)
                cookies[name.strip()] = value.strip()
        
        return cookies
    
    def cookies_to_string(self, cookies_dict):
        """تحويل dictionary الكوكيز إلى سلسلة"""
        return '; '.join([f"{k}={v}" for k, v in cookies_dict.items()])
    
    def update_cookies_from_response(self, response):
        """تحديث الكوكيز من استجابة HTTP"""
        if 'set-cookie' in response.headers:
            set_cookie_header = response.headers.get('set-cookie', '')
            if set_cookie_header:
                # معالجة كل كوكي في الـ set-cookie header
                cookie_lines = set_cookie_header.split(', ')
                for cookie_line in cookie_lines:
                    cookie_parts = cookie_line.split(';')
                    if '=' in cookie_parts[0]:
                        name, value = cookie_parts[0].split('=', 1)
                        self.cookies[name] = value
                
                # تحديث جلسة requests
                self.session.cookies.clear()
                for name, value in self.cookies.items():
                    self.session.cookies.set(name, value)
                
                # حفظ الكوكيز الجديدة في ملف config
                self.save_cookies_to_config()
                
                print(f"[{self.timestamp()}] Cookies updated from response")
                return True
        return False
    
    def save_cookies_to_config(self):
        """حفظ الكوكيز الجديدة في ملف config.telegram.py"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'telegram.py')
            
            # قراءة الملف
            with open(config_path, 'r') as f:
                content = f.read()
            
            # إنشاء سلسلة الكوكيز الجديدة
            new_cookie_string = self.cookies_to_string(self.cookies)
            
            # تحديث COOKIE_STRING في الملف
            import re
            # البحث عن COOKIE_STRING وتحديثها
            new_content = re.sub(
                r'COOKIE_STRING\s*=\s*".*?"',
                f'COOKIE_STRING = "{new_cookie_string}"',
                content
            )
            
            # إذا لم تجد النمط، أضفه في النهاية
            if new_content == content:
                new_content = content.replace(
                    'COOKIE_STRING = ""',
                    f'COOKIE_STRING = "{new_cookie_string}"'
                )
            
            # حفظ الملف
            with open(config_path, 'w') as f:
                f.write(new_content)
            
            print(f"[{self.timestamp()}] Cookies saved to config file")
            
        except Exception as e:
            print(f"[{self.timestamp()}] Error saving cookies to config: {e}")
    
    def refresh_with_login(self):
        """تجديد الكوكيز عن طريق تسجيل الدخول"""
        try:
            login_url = "https://agents.ichancy.com/global/api/User/signIn"
            
            payload = {
                "username": "jadobot@jado.nsp",
                "password": "Jado1993@@"
            }
            
            headers = {
                'Content-Type': 'application/json',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                'origin': 'https://agents.ichancy.com',
                'referer': 'https://agents.ichancy.com/'
            }
            
            print(f"[{self.timestamp()}] Attempting login to refresh cookies...")
            
            response = requests.post(login_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # تحديث الكوكيز من الاستجابة
                if self.update_cookies_from_response(response):
                    print(f"[{self.timestamp()}] Login successful, cookies refreshed")
                    self.last_refresh = time.time()
                    self.failed_attempts = 0
                    return True
                else:
                    print(f"[{self.timestamp()}] Login succeeded but no cookies in response")
            else:
                print(f"[{self.timestamp()}] Login failed with status: {response.status_code}")
            
            self.failed_attempts += 1
            return False
            
        except Exception as e:
            print(f"[{self.timestamp()}] Login error: {e}")
            self.failed_attempts += 1
            return False
    
    def make_request(self, url, payload=None, method="POST"):
        """إجراء طلب HTTP مع معالجة الأخطاء"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                'origin': 'https://agents.ichancy.com',
                'referer': 'https://agents.ichancy.com/dashboard'
            }
            
            # تحديث الكوكيز في الهيدرات
            headers['cookie'] = self.cookies_to_string(self.cookies)
            
            if method.upper() == "POST":
                response = self.session.post(url, json=payload, headers=headers, timeout=30)
            else:
                response = self.session.get(url, headers=headers, timeout=30)
            
            # تحديث الكوكيز من الاستجابة
            self.update_cookies_from_response(response)
            
            return response
            
        except Exception as e:
            print(f"[{self.timestamp()}] Request error to {url}: {e}")
            return None
    
    def keep_alive(self):
        """الحفاظ على الجلسة نشطة"""
        urls = [
            "https://agents.ichancy.com/global/api/core/getData",
            "https://agents.ichancy.com/global/api/Agent/getAgentWallet",
            "https://agents.ichancy.com/global/api/Statistics/getPlayersStatisticsPro"
        ]
        
        print("=" * 60)
        print(f"[{self.timestamp()}] iChancy Session Keeper Started")
        print(f"[{self.timestamp()}] Refresh interval: 20 minutes")
        print("=" * 60)
        
        try:
            while True:
                current_time = time.time()
                
                # التحقق إذا حان وقت التجديد
                if current_time - self.last_refresh > self.refresh_interval:
                    print(f"[{self.timestamp()}] Time for cookie refresh...")
                    if not self.refresh_with_login():
                        print(f"[{self.timestamp()}] Refresh failed, waiting 1 minute...")
                        time.sleep(60)
                        continue
                
                # إجراء طلب عشوائي للحفاظ على النشاط
                import random
                url = random.choice(urls)
                
                print(f"[{self.timestamp()}] Making request to: {url.split('/')[-1]}")
                
                response = self.make_request(url, {})
                
                if response is None:
                    print(f"[{self.timestamp()}] Request failed, waiting 30 seconds...")
                    time.sleep(30)
                    continue
                
                if response.status_code == 200:
                    print(f"[{self.timestamp()}] Request successful (Status: 200)")
                elif response.status_code == 403:
                    print(f"[{self.timestamp()}] Got 403, cookies may be expired")
                    # حاول التجديد فوراً
                    if not self.refresh_with_login():
                        print(f"[{self.timestamp()}] Immediate refresh failed")
                else:
                    print(f"[{self.timestamp()}] Request status: {response.status_code}")
                
                # انتظر فترة عشوائية بين 30-90 ثانية
                wait_time = random.uniform(30, 90)
                print(f"[{self.timestamp()}] Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                
        except KeyboardInterrupt:
            print(f"\n[{self.timestamp()}] Session keeper stopped by user")
        except Exception as e:
            print(f"[{self.timestamp()}] Unexpected error: {e}")

if __name__ == "__main__":
    keeper = SessionKeeper()
    keeper.keep_alive()