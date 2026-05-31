import requests
import time
import os
import re
import random
from datetime import datetime
import json

print("=" * 60)
print("iChancy Cookie Auto-Refresh Service")
print("=" * 60)

class CookieAutoService:
    def __init__(self):
        self.config_file = "config/telegram.py"
        self.ichancy_config = "config/ichancy.py"
        
        # ﻂﺑاﻭﺭ API
        self.login_url = "https://agents.ichancy.com/global/api/User/signIn"
        self.test_urls = [
            "https://agents.ichancy.com/global/api/core/getData",
            "https://agents.ichancy.com/global/api/Agent/getAgentWallet"
        ]
        
        # ﻝﻮﺧﺪﻟا ﻞﻴﺠﺴﺗ ﺕﺎﻧﺎﻴﺑ
        self.login_username = "jadobot@jado.nsp"
        self.login_password = "Jado1993@@"
        
        # ﺕاﺩاﺪﻋﺇ
        self.refresh_interval = 20 * 60  # 20 ﺔﻘﻴﻗﺩ
        self.last_refresh = 0
        
        print(f"[{self.time_now()}] Service initialized")
        print(f"[{self.time_now()}] Refresh interval: {self.refresh_interval//60} minutes")
        print(f"[{self.time_now()}] Username: {self.login_username}")
    
    def time_now(self):
        return datetime.now().strftime('%H:%M:%S')
    
    def parse_cookies(self, cookie_string):
        """ﺱﻮﻣﺎﻗ ﻰﻟﺇ ﺰﻴﻛﻮﻜﻟا ﺔﻠﺴﻠﺳ ﻞﻳﻮﺤﺗ"""
        cookies = {}
        if not cookie_string:
            return cookies
        
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key] = value
        
        return cookies
    
    def cookies_to_string(self, cookies_dict):
        """ﺔﻠﺴﻠﺳ ﻰﻟﺇ ﺰﻴﻛﻮﻜﻟا ﺱﻮﻣﺎﻗ ﻞﻳﻮﺤﺗ"""
        return '; '.join([f"{k}={v}" for k, v in cookies_dict.items()])
    
    def login_and_refresh(self):
        """ﺰﻴﻛﻮﻜﻟا ﺪﻳﺪﺠﺘﻟ ﻝﻮﺧﺪﻟا ﻞﻴﺠﺴﺗ"""
        try:
            print(f"[{self.time_now()}] Logging in to refresh cookies...")
            
            login_data = {
                "username": self.login_username,
                "password": self.login_password
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                'Content-Type': 'application/json'
            }
            
            # ﻝﻮﺧﺪﻟا ﻞﻴﺠﺴﺗ ﺐﻠﻃ ﻝﺎﺳﺭﺇ
            response = requests.post(
                self.login_url,
                json=login_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                # ﺰﻴﻛﻮﻜﻟا ﻰﻠﻋ ﻝﻮﺼﺤﻟا
                cookies = response.cookies.get_dict()
                
                # ﻦﻣ ﺰﻴﻛﻮﻜﻟا ﺔﻓﺎﺿﺇ headers ﺕﺪﺟﻭ اﺫﺇ
                if 'set-cookie' in response.headers:
                    set_cookie_header = response.headers['set-cookie']
                    for cookie_item in set_cookie_header.split(','):
                        if '=' in cookie_item:
                            parts = cookie_item.split(';')[0]
                            if '=' in parts:
                                key, value = parts.split('=', 1)
                                cookies[key.strip()] = value.strip()
                
                if cookies:
                    # ﻒﻠﻣ ﺚﻳﺪﺤﺗ config
                    if self.update_config_file(cookies):
                        self.last_refresh = time.time()
                        print(f"[{self.time_now()}] ✓ Login successful! Updated {len(cookies)} cookies")
                        return True
                else:
                    print(f"[{self.time_now()}] No cookies received")
            else:
                print(f"[{self.time_now()}] Login failed with status: {response.status_code}")
                
        except Exception as e:
            print(f"[{self.time_now()}] Login error: {str(e)}")
        
        return False
    
    def update_config_file(self, cookies_dict):
        """ﻒﻠﻣ ﺚﻳﺪﺤﺗ config ﺓﺪﻳﺪﺠﻟا ﺰﻴﻛﻮﻜﻟﺎﺑ"""
        try:
            # ﺔﻠﺴﻠﺳ ﻰﻟﺇ ﺰﻴﻛﻮﻜﻟا ﻞﻳﻮﺤﺗ
            new_cookie_string = self.cookies_to_string(cookies_dict)
            
            # ﻒﻠﻤﻟا ﺓءاﺮﻗ
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            # ﺚﻳﺪﺤﺗ COOKIE_STRING
            new_content = re.sub(
                r'COOKIE_STRING\s*=\s*".*?"',
                f'COOKIE_STRING = "{new_cookie_string}"',
                content
            )
            
            # ﻰﻠﻋ ﺭﻮﺜﻌﻟا ﻢﺘﻳ ﻢﻟ اﺫﺇ COOKIE_STRING، ﻪﻔﺿﺃ
            if new_content == content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'TOKEN = ' in line:
                        lines.insert(i + 1, f'COOKIE_STRING = "{new_cookie_string}"')
                        new_content = '\n'.join(lines)
                        break
            
            # ﻒﻠﻤﻟا ﻆﻔﺣ
            with open(self.config_file, 'w') as f:
                f.write(new_content)
            
            return True
            
        except Exception as e:
            print(f"[{self.time_now()}] Error updating config: {e}")
            return False
    
    def test_connection(self):
        """ﻊﻗﻮﻤﻟﺎﺑ ﻝﺎﺼﺗﻻا ﺭﺎﺒﺘﺧا"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
            }
            
            response = requests.get("https://agents.ichancy.com", headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def run_service(self):
        """ﺔﻴﺴﻴﺋﺮﻟا ﺔﻣﺪﺨﻟا ﻞﻴﻐﺸﺗ"""
        print(f"[{self.time_now()}] Starting service...")
        
        # ًﻻﻭﺃ ﻝﺎﺼﺗﻻا ﺭﺎﺒﺘﺧا
        if not self.test_connection():
            print(f"[{self.time_now()}] ✗ Cannot connect to iChancy website")
            return
        
        # ﻲﻟﻭﺃ ﺪﻳﺪﺠﺗ
        print(f"[{self.time_now()}] Performing initial cookie refresh...")
        if self.login_and_refresh():
            print(f"[{self.time_now()}] ✓ Initial refresh successful")
        else:
            print(f"[{self.time_now()}] ✗ Initial refresh failed")
            print(f"[{self.time_now()}] Will retry in 5 minutes...")
            time.sleep(300)
        
        cycle = 0
        
        try:
            while True:
                cycle += 1
                current_time = time.time()
                
                # ﺪﻳﺪﺠﺘﻟا ﺖﻗﻭ ﻦﻣ ﻖﻘﺤﺘﻟا
                if current_time - self.last_refresh >= self.refresh_interval:
                    print(f"\n[{self.time_now()}] Cycle {cycle}: Refreshing cookies...")
                    if self.login_and_refresh():
                        print(f"[{self.time_now()}] Refresh successful")
                    else:
                        print(f"[{self.time_now()}] Refresh failed, will retry later")
                
                # ﺔﻘﻴﻗﺩ 2-1 ﺭﺎﻈﺘﻧا
                wait_time = random.uniform(60, 120)
                print(f"[{self.time_now()}] Next check in {wait_time:.0f} seconds...", end='\r')
                time.sleep(wait_time)
                
        except KeyboardInterrupt:
            print(f"\n\n[{self.time_now()}] Service stopped by user")
        except Exception as e:
            print(f"\n[{self.time_now()}] Service error: {e}")


def main():
    print("\n" + "="*60)
    print("iChancy Cookie Auto-Refresh Service")
    print("="*60)
    
    # ﺕﺎﻔﻠﻣ ﻦﻣ ﻖﻘﺤﺘﻟا config
    if not os.path.exists("config"):
        print("ERROR: 'config' directory not found!")
        return
    
    if not os.path.exists("config/telegram.py"):
        print("ERROR: config/telegram.py not found!")
        return
    
    # ﺔﻣﺪﺨﻟا ءﺪﺑ
    service = CookieAutoService()
    service.run_service()


if __name__ == "__main__":
    main()