"""
iChancy Agent API Client
========================
Connects to agents.ichancy.com API using Playwright browser automation
with stealth mode to bypass Cloudflare protection.

Strategy:
  1. Launch headless Firefox with playwright-stealth
  2. Navigate to login page, fill credentials, submit
  3. Extract access token from localStorage
  4. Extract cookies from browser context
  5. Use token + cookies for subsequent API calls via httpx

Fallback:
  - Manual token via ICHANCY_ACCESS_TOKEN env var
  - Direct API calls with token (no browser) if Cloudflare
    doesn't block API endpoints after authentication
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try importing Playwright
try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("playwright not installed - browser-based auth unavailable")

try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    logger.warning("playwright-stealth not installed - stealth mode unavailable")

# HTTP client for API calls
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import requests as raw_requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class iChancyAPI:
    """
    iChancy Agent API client using Playwright browser automation.

    Uses a real Firefox browser with stealth mode to bypass Cloudflare,
    then extracts the access token and cookies for subsequent API calls.
    """

    BASE_URL = 'https://agents.ichancy.com'
    API_BASE = f'{BASE_URL}/global/api'

    # Singleton-like shared session
    _shared_instance = None
    _last_auth_time = None
    _auth_ttl = timedelta(minutes=55)  # Token valid for 1hr, refresh at 55min

    # Cached browser cookies (class-level for reuse)
    _browser_cookies = None

    # Pre-authentication state
    _pre_auth_done = False
    _pre_auth_task = None

    @classmethod
    def get_shared(cls):
        """Get or create a shared API instance."""
        now = datetime.now()
        if cls._shared_instance is None or (cls._last_auth_time and now - cls._last_auth_time > cls._auth_ttl):
            # Preserve tokens if instance exists and token not expired yet
            old_token = cls._shared_instance.access_token if cls._shared_instance else None
            old_token_expires = cls._shared_instance.token_expires_at if cls._shared_instance else None
            old_cookies = cls._browser_cookies

            cls._shared_instance = cls()
            cls._last_auth_time = now

            # Restore token if still valid (avoid unnecessary re-auth)
            if old_token and old_token_expires and datetime.now() < old_token_expires:
                cls._shared_instance.access_token = old_token
                cls._shared_instance.token_expires_at = old_token_expires
                cls._shared_instance._authenticated = True
                cls._browser_cookies = old_cookies
                logger.info("Restored valid token from previous instance")
        return cls._shared_instance

    @classmethod
    def reset_shared(cls):
        """Reset the shared instance to force re-authentication."""
        cls._shared_instance = None
        cls._last_auth_time = None
        cls._browser_cookies = None
        cls._pre_auth_done = False

    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.agent_id = None
        self._http_client = None
        self._authenticated = False

        # Check for manual token first (env var ICHANCY_ACCESS_TOKEN)
        manual_token = os.getenv('ICHANCY_ACCESS_TOKEN', '').strip()
        if manual_token:
            self.access_token = manual_token
            self.token_expires_at = datetime.now() + timedelta(hours=1)
            self._authenticated = True
            logger.info("Using manually provided ICHANCY_ACCESS_TOKEN")

        # Initialize HTTP client
        self._init_http_client()

    def _init_http_client(self):
        """Initialize the HTTP client for API calls."""
        if HAS_HTTPX:
            self._http_client = httpx.AsyncClient(
                timeout=60.0,
                follow_redirects=True,
            )
        elif HAS_REQUESTS:
            self._http_client = None  # Will use sync requests as fallback
        else:
            raise RuntimeError("No HTTP library available (need httpx or requests)")

    async def _get_cookies_dict(self):
        """Get cookies as a dict for HTTP requests."""
        cookies = {}
        if iChancyAPI._browser_cookies:
            for cookie in iChancyAPI._browser_cookies:
                cookies[cookie.get('name', '')] = cookie.get('value', '')
        return cookies

    async def _get_headers(self, with_auth=True):
        """Return headers dict with auth token and browser-like headers."""
        h = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'Origin': self.BASE_URL,
            'Referer': self.BASE_URL + '/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Connection': 'keep-alive',
        }
        if with_auth and self.access_token:
            h['Authorization'] = f'Bearer {self.access_token}'
        return h

    async def _api_post(self, url, payload, timeout=60):
        """Make an async POST request to the iChancy API."""
        headers = await self._get_headers(with_auth=True)
        cookies = await self._get_cookies_dict()

        if HAS_HTTPX and self._http_client:
            try:
                response = await self._http_client.post(
                    url,
                    json=payload,
                    headers=headers,
                    cookies=cookies,
                    timeout=timeout,
                )
                return response
            except Exception as e:
                logger.error(f"httpx POST error: {e}")
                # Fallback to sync requests
                return await asyncio.to_thread(
                    self._sync_post, url, payload, headers, cookies, timeout
                )
        elif HAS_REQUESTS:
            return await asyncio.to_thread(
                self._sync_post, url, payload, headers, cookies, timeout
            )
        else:
            raise RuntimeError("No HTTP library available")

    def _sync_post(self, url, payload, headers, cookies, timeout):
        """Synchronous POST fallback using requests."""
        session = raw_requests.Session()
        for name, value in cookies.items():
            session.cookies.set(name, value, domain='agents.ichancy.com')
        response = session.post(url, json=payload, headers=headers, timeout=timeout)
        session.close()
        return response

    async def _api_get(self, url, timeout=60):
        """Make an async GET request to the iChancy API."""
        headers = await self._get_headers(with_auth=True)
        cookies = await self._get_cookies_dict()

        if HAS_HTTPX and self._http_client:
            try:
                response = await self._http_client.get(
                    url,
                    headers=headers,
                    cookies=cookies,
                    timeout=timeout,
                )
                return response
            except Exception as e:
                logger.error(f"httpx GET error: {e}")
                return await asyncio.to_thread(
                    self._sync_get, url, headers, cookies, timeout
                )
        elif HAS_REQUESTS:
            return await asyncio.to_thread(
                self._sync_get, url, headers, cookies, timeout
            )
        else:
            raise RuntimeError("No HTTP library available")

    def _sync_get(self, url, headers, cookies, timeout):
        """Synchronous GET fallback using requests."""
        session = raw_requests.Session()
        for name, value in cookies.items():
            session.cookies.set(name, value, domain='agents.ichancy.com')
        response = session.get(url, headers=headers, timeout=timeout)
        session.close()
        return response

    # =============================
    # BROWSER-BASED AUTHENTICATION
    # =============================
    async def _browser_signin(self, username, password):
        """
        Sign in using Playwright browser automation with stealth mode.
        Uses Firefox browser to bypass Cloudflare protection.
        """
        if not HAS_PLAYWRIGHT:
            logger.error("Playwright not available for browser-based sign-in")
            return False

        browser = None
        try:
            async with async_playwright() as p:
                # Launch headless Firefox (no Chromium-specific args needed)
                browser = await p.firefox.launch(
                    headless=True,
                )

                # Create context with realistic viewport and user agent
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
                    locale="en-US",
                )

                page = await context.new_page()

                # Apply stealth mode if available
                if HAS_STEALTH:
                    await stealth_async(page)
                    logger.info("Stealth mode applied to Firefox browser page")

                # Navigate to login page
                logger.info(f"Navigating to {self.BASE_URL}/login with Firefox ...")
                try:
                    await page.goto(f"{self.BASE_URL}/login", wait_until="networkidle", timeout=60000)
                except Exception as nav_err:
                    logger.warning(f"networkidle timeout on login page, trying domcontentloaded: {nav_err}")
                    try:
                        await page.goto(f"{self.BASE_URL}/login", wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_timeout(5000)
                    except Exception as nav_err2:
                        logger.error(f"Failed to navigate to login page: {nav_err2}")
                        await browser.close()
                        return False

                # FAST CHECK: Detect Cloudflare block page immediately
                # If the server IP is blocked, no amount of waiting will help
                try:
                    page_title = (await page.title() or '').lower()
                    if 'cloudflare' in page_title or 'attention required' in page_title or 'blocked' in page_title:
                        logger.error(f"Cloudflare BLOCKED this server IP! Page title: {await page.title()}")
                        logger.error("The Railway server IP has been blocked by Cloudflare. "
                                     "Set ICHANCY_ACCESS_TOKEN env var manually or use a proxy.")
                        await browser.close()
                        return False
                except Exception:
                    pass

                # Wait for the login form to appear
                logger.info("Login page loaded, filling credentials...")

                # Try multiple selectors for the username/email field
                username_selectors = [
                    'input[name="username"]',
                    'input[type="email"]',
                    'input[placeholder*="user" i]',
                    'input[placeholder*="email" i]',
                    'input[id*="user" i]',
                    'input[id*="email" i]',
                ]

                username_filled = False
                for selector in username_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            await element.click()
                            await element.fill(username)
                            username_filled = True
                            logger.info(f"Filled username with selector: {selector}")
                            break
                    except Exception:
                        continue

                if not username_filled:
                    logger.error("Could not find username/email input field")
                    # Take screenshot for debugging
                    try:
                        current_url = page.url
                        page_title = await page.title()
                        logger.error(f"Page debug: URL={current_url}, Title={page_title}")
                        await page.screenshot(path="/tmp/login_page_error.png")
                        logger.info("Screenshot saved to /tmp/login_page_error.png")
                    except Exception:
                        pass
                    await browser.close()
                    return False

                # Try multiple selectors for the password field
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[placeholder*="password" i]',
                    'input[id*="password" i]',
                ]

                password_filled = False
                for selector in password_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            await element.click()
                            await element.fill(password)
                            password_filled = True
                            logger.info(f"Filled password with selector: {selector}")
                            break
                    except Exception:
                        continue

                if not password_filled:
                    logger.error("Could not find password input field")
                    await browser.close()
                    return False

                # Click submit button
                submit_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    'button:has-text("تسجيل")',
                    'input[type="submit"]',
                ]

                submitted = False
                for selector in submit_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            await element.click()
                            submitted = True
                            logger.info(f"Clicked submit with selector: {selector}")
                            break
                    except Exception:
                        continue

                if not submitted:
                    logger.error("Could not find submit button")
                    await browser.close()
                    return False

                # Wait for navigation after login
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    logger.warning("Timeout waiting for networkidle after login, continuing...")

                # Additional wait for any async token storage
                await page.wait_for_timeout(3000)

                # Extract token from localStorage
                token_data = await page.evaluate("""() => {
                    return {
                        accessToken: localStorage.getItem('accessToken') || localStorage.getItem('token'),
                        refreshToken: localStorage.getItem('refreshToken'),
                        allKeys: Object.keys(localStorage)
                    };
                }""")

                logger.info(f"localStorage keys found: {token_data.get('allKeys', [])}")

                self.access_token = token_data.get("accessToken")
                self.refresh_token = token_data.get("refreshToken")

                # Extract cookies from browser context
                iChancyAPI._browser_cookies = await context.cookies()
                logger.info(f"Extracted {len(iChancyAPI._browser_cookies)} cookies from browser")

                await browser.close()
                browser = None

                if self.access_token:
                    self.token_expires_at = datetime.now() + timedelta(hours=1)
                    self._authenticated = True
                    logger.info("Successfully obtained access token via Firefox browser sign-in")
                    iChancyAPI._last_auth_time = datetime.now()
                    return True
                else:
                    logger.error("No access token found in localStorage after login")
                    return False

        except Exception as e:
            logger.error(f"Firefox browser sign-in error: {e}", exc_info=True)
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            return False

    # =============================
    # AUTHENTICATION
    # =============================
    async def ensure_authenticated(self):
        """Ensure we have a valid access token. Uses browser sign-in if needed."""
        try:
            # Check manual token first (highest priority - set via env var)
            manual_token = os.getenv('ICHANCY_ACCESS_TOKEN', '').strip()
            if manual_token:
                if self.access_token != manual_token:
                    self.access_token = manual_token
                    self.token_expires_at = datetime.now() + timedelta(hours=1)
                    self._authenticated = True
                    logger.info("Using manually provided ICHANCY_ACCESS_TOKEN from env var")
                return True

            # Check if token is still valid
            if self.access_token and not self._is_token_expired():
                return True

            # Need to re-authenticate
            logger.info("Token expired or missing, performing browser sign-in...")
            return await self._do_signin()

        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return False

    @classmethod
    async def pre_authenticate(cls):
        """Pre-authenticate at bot startup so first user request is instant.
        This runs the browser sign-in once when the bot starts, so that
        when a user requests account creation, the token is already available
        and the API call takes only 1-2 seconds instead of 20-40 seconds.
        """
        if cls._pre_auth_done:
            return True

        try:
            logger.info("🔄 Pre-authenticating with iChancy servers (startup)...")
            api = cls.get_shared()
            success = await api.ensure_authenticated()

            if success:
                cls._pre_auth_done = True
                logger.info("✅ Pre-authentication successful! API calls will be instant.")
            else:
                logger.warning("⚠️ Pre-authentication failed - will retry on first user request")

            return success
        except Exception as e:
            logger.error(f"Pre-authentication error: {e}")
            return False

    @classmethod
    async def start_auto_refresh(cls):
        """Background task that refreshes the token before it expires.
        Runs every 50 minutes to ensure the token never expires during use.
        """
        while True:
            try:
                await asyncio.sleep(50 * 60)  # 50 minutes
                logger.info("🔄 Auto-refreshing iChancy authentication token...")
                cls.reset_shared()
                api = cls.get_shared()
                success = await api.ensure_authenticated()
                if success:
                    logger.info("✅ Auto-refresh successful")
                else:
                    logger.warning("⚠️ Auto-refresh failed - will retry on next API call")
            except Exception as e:
                logger.error(f"Auto-refresh error: {e}")
                await asyncio.sleep(60)  # Wait 1 min before retry

    async def _do_signin(self):
        """Perform sign-in using the best available method."""
        username = os.getenv('ICHANCY_USERNAME', '').strip()
        password = os.getenv('ICHANCY_PASSWORD', '').strip()

        if not username or not password:
            # Fallback to config file
            try:
                import config.telegram as cfg
                username = username or getattr(cfg, 'ICHANCY_USERNAME', '')
                password = password or getattr(cfg, 'ICHANCY_PASSWORD', '')
            except Exception:
                pass

        if not username or not password:
            logger.error("MISSING iChancy credentials (ICHANCY_USERNAME / ICHANCY_PASSWORD)")
            return False

        # Try browser-based sign-in (best Cloudflare bypass)
        if HAS_PLAYWRIGHT:
            logger.info("Attempting browser-based sign-in with Playwright Firefox...")
            for attempt in range(2):
                try:
                    success = await self._browser_signin(username, password)
                    if success:
                        return True
                    logger.warning(f"Browser sign-in attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Browser sign-in attempt {attempt + 1} error: {e}")
                    await asyncio.sleep(2)

        # Fallback: try direct API sign-in (may work if Cloudflare isn't blocking)
        logger.info("Trying direct API sign-in as fallback...")
        return await self._direct_api_signin(username, password)

    async def _direct_api_signin(self, username, password):
        """Fallback: Try direct API sign-in without browser."""
        try:
            url = f"{self.API_BASE}/UserApi/signin"
            payload = {"username": username, "password": password}

            headers = {
                'Content-Type': 'application/json',
                'Origin': self.BASE_URL,
                'Referer': self.BASE_URL + '/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            }

            if HAS_HTTPX and self._http_client:
                response = await self._http_client.post(
                    url, json=payload, headers=headers, timeout=30
                )
            elif HAS_REQUESTS:
                response = await asyncio.to_thread(
                    raw_requests.post, url, json=payload, headers=headers, timeout=30
                )
            else:
                return False

            status = response.status_code if hasattr(response, 'status_code') else 0

            if status == 403:
                logger.warning("Direct API sign-in blocked by Cloudflare (403)")
                return False

            if status != 200:
                logger.error(f"Direct API sign-in failed with HTTP {status}")
                return False

            data = response.json() if hasattr(response, 'json') else {}
            if callable(data):
                data = data()

            if not data.get('status'):
                logger.error("API returned status=false")
                return False

            result = data.get('result', {})
            self.access_token = result.get('accessToken')
            self.refresh_token = result.get('refreshToken')

            if self.access_token:
                self.token_expires_at = datetime.now() + timedelta(hours=1)
                self._authenticated = True
                logger.info("Direct API sign-in successful")
                return True
            else:
                logger.error("No access token from direct API sign-in")
                return False

        except Exception as e:
            logger.error(f"Direct API sign-in error: {e}")
            return False

    def _is_token_expired(self):
        """Check if the current token has expired."""
        if not self.token_expires_at:
            return True
        return datetime.now() >= self.token_expires_at

    # =============================
    # PLAYER MANAGEMENT
    # =============================
    async def register_player(self, username, password, email, parent_id=None):
        """Register a new player using the API."""
        if not await self.ensure_authenticated():
            return {'success': False, 'error': 'فشل في المصادقة مع خوادم iChancy - يرجى المحاولة لاحقاً'}

        try:
            url = f"{self.API_BASE}/UserApi/registerPlayer"

            if not parent_id:
                parent_id = os.getenv('ICHANCY_PARENT_ID', '2613607')
                if not parent_id or parent_id == '2613607':
                    parent_id = os.getenv('PARENT_ID', parent_id)

            parent_id = str(parent_id)

            payload = {
                "player": {
                    "login": username,
                    "email": email,
                    "password": password,
                    "parentId": parent_id
                }
            }

            logger.info(f"Registering player: {username}, parent_id: {parent_id}")

            response = await self._api_post(url, payload, timeout=60)
            status = response.status_code if hasattr(response, 'status_code') else 0

            logger.info(f"Register response status: {status}")

            if status == 403:
                # Try re-authenticating and retrying
                logger.warning("Got 403 on register, re-authenticating...")
                iChancyAPI.reset_shared()
                if await self.ensure_authenticated():
                    response = await self._api_post(url, payload, timeout=60)
                    status = response.status_code if hasattr(response, 'status_code') else 0
                    logger.info(f"Register retry status: {status}")

                if status == 403:
                    return {'success': False, 'error': 'Cloudflare يحظر الاتصال - يرجى المحاولة لاحقاً'}

            if status == 422:
                try:
                    data = response.json() if hasattr(response, 'json') else {}
                    if callable(data):
                        data = data()
                    notifications = data.get('notification', [])
                    if notifications:
                        error_msg = notifications[0].get('content', 'خطأ في التحقق')
                        return {'success': False, 'error': error_msg}
                except Exception:
                    pass
                return {'success': False, 'error': 'خطأ في التحقق من البيانات'}

            if status != 200:
                return {'success': False, 'error': f'خطأ HTTP {status}'}

            try:
                data = response.json() if hasattr(response, 'json') else {}
                if callable(data):
                    data = data()
            except Exception:
                return {'success': False, 'error': 'استجابة غير صالحة من الخادم'}

            if not data.get('status'):
                notifications = data.get('notification', [])
                if notifications:
                    error_msg = notifications[0].get('content', 'فشل التسجيل')
                    return {'success': False, 'error': error_msg}
                return {'success': False, 'error': 'فشل التسجيل'}

            player_id = data.get('result')
            logger.info(f"Registration successful! Player ID: {player_id}")
            return {'success': True, 'player_id': player_id, 'data': data}

        except Exception as e:
            logger.error(f"Register player exception: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def get_players_for_current_agent(self, player_id=None, username=None, limit=20):
        """Get players for the current agent."""
        if not await self.ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}

        try:
            url = f"{self.API_BASE}/UserApi/getPlayersForCurrentAgent"

            payload = {
                "start": 0,
                "limit": limit,
                "filter": {}
            }

            if player_id:
                payload["filter"]["playerId"] = {
                    "action": "=",
                    "value": str(player_id),
                    "valueLabel": str(player_id)
                }
            elif username:
                payload["filter"]["userName"] = {
                    "action": "=",
                    "value": username,
                    "valueLabel": username
                }

            response = await self._api_post(url, payload, timeout=30)
            status = response.status_code if hasattr(response, 'status_code') else 0

            if status == 403:
                iChancyAPI.reset_shared()
                if await self.ensure_authenticated():
                    response = await self._api_post(url, payload, timeout=30)
                    status = response.status_code if hasattr(response, 'status_code') else 0

            if status != 200:
                return {'success': False, 'error': f'HTTP {status}'}

            try:
                data = response.json() if hasattr(response, 'json') else {}
                if callable(data):
                    data = data()
            except Exception:
                return {'success': False, 'error': 'Invalid JSON response'}

            if not data.get('status'):
                return {'success': False, 'error': 'API request failed'}

            result = data.get('result', {})
            records = result.get('records', []) if result else []

            if records:
                return {'success': True, 'player': records[0], 'data': data}
            else:
                return {'success': False, 'error': 'Player not found'}

        except Exception as e:
            logger.error(f"Get players exception: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def get_player_id_by_username(self, username):
        """Get player ID by username."""
        result = await self.get_players_for_current_agent(username=username)
        if result.get('success') and result.get('player'):
            return result['player'].get('id') or result['player'].get('playerId')
        return None

    async def get_player_balance_by_id(self, player_id):
        """Get player balance by ID."""
        if not await self.ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}

        try:
            url = f"{self.API_BASE}/UserApi/getPlayerBalanceById"
            payload = {"playerId": player_id}

            response = await self._api_post(url, payload, timeout=30)
            status = response.status_code if hasattr(response, 'status_code') else 0

            if status == 403:
                iChancyAPI.reset_shared()
                if await self.ensure_authenticated():
                    response = await self._api_post(url, payload, timeout=30)
                    status = response.status_code if hasattr(response, 'status_code') else 0

            if status != 200:
                return {'success': False, 'error': f'HTTP {status}'}

            try:
                data = response.json() if hasattr(response, 'json') else {}
                if callable(data):
                    data = data()
            except Exception:
                return {'success': False, 'error': 'Invalid JSON response'}

            if not data.get('status'):
                return {'success': False, 'error': 'API request failed'}

            balances = data.get('result', [])
            if balances:
                balance_info = balances[0]
                return {'success': True, 'balance': balance_info.get('balance', 0), 'data': data}
            else:
                return {'success': True, 'balance': 0, 'data': data}

        except Exception as e:
            logger.error(f"Get player balance error: {e}")
            return {'success': False, 'error': str(e)}

    async def get_player_balance_by_username(self, username):
        """Get player balance by username."""
        player_result = await self.get_players_for_current_agent(username=username)
        if not player_result.get('success'):
            return player_result

        player = player_result.get('player', {})
        player_id = player.get('id') or player.get('playerId')
        if not player_id:
            return {'success': False, 'error': 'Player not found'}

        return await self.get_player_balance_by_id(player_id)

    # =============================
    # TRANSACTIONS
    # =============================
    async def deposit_to_player(self, player_id, amount, comment="Bot deposit", currency="NSP"):
        """Deposit money to player account."""
        if not await self.ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}

        try:
            url = f"{self.API_BASE}/UserApi/depositToPlayer"
            payload = {
                "amount": float(amount),
                "comment": comment,
                "playerId": player_id,
                "currencyCode": currency,
                "currency": currency,
                "moneyStatus": 5
            }

            logger.info(f"Depositing {amount} {currency} to player {player_id}")
            response = await self._api_post(url, payload, timeout=30)
            status = response.status_code if hasattr(response, 'status_code') else 0

            if status == 403:
                iChancyAPI.reset_shared()
                if await self.ensure_authenticated():
                    response = await self._api_post(url, payload, timeout=30)
                    status = response.status_code if hasattr(response, 'status_code') else 0

            if status != 200:
                return {'success': False, 'error': f'HTTP {status}'}

            try:
                data = response.json() if hasattr(response, 'json') else {}
                if callable(data):
                    data = data()
            except Exception:
                return {'success': False, 'error': 'Invalid JSON response'}

            if not data.get('status'):
                notifications = data.get('notification', [])
                if notifications:
                    error_msg = notifications[0].get('content', 'Deposit failed')
                    return {'success': False, 'error': error_msg}
                return {'success': False, 'error': 'Deposit failed'}

            logger.info(f"Deposit successful for player {player_id}")
            return {'success': True, 'data': data}

        except Exception as e:
            logger.error(f"Deposit error: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def withdraw_from_player(self, player_id, amount, comment="Bot withdraw", currency="NSP"):
        """Withdraw money from player account."""
        if not await self.ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}

        try:
            url = f"{self.API_BASE}/UserApi/withdrawFromPlayer"
            payload = {
                "amount": float(amount),
                "comment": comment,
                "playerId": player_id,
                "currencyCode": currency,
                "currency": currency,
                "moneyStatus": 5
            }

            logger.info(f"Withdrawing {amount} {currency} from player {player_id}")
            response = await self._api_post(url, payload, timeout=30)
            status = response.status_code if hasattr(response, 'status_code') else 0

            if status == 403:
                iChancyAPI.reset_shared()
                if await self.ensure_authenticated():
                    response = await self._api_post(url, payload, timeout=30)
                    status = response.status_code if hasattr(response, 'status_code') else 0

            if status != 200:
                return {'success': False, 'error': f'HTTP {status}'}

            try:
                data = response.json() if hasattr(response, 'json') else {}
                if callable(data):
                    data = data()
            except Exception:
                return {'success': False, 'error': 'Invalid JSON response'}

            if not data.get('status'):
                notifications = data.get('notification', [])
                if notifications:
                    error_msg = notifications[0].get('content', 'Withdrawal failed')
                    return {'success': False, 'error': error_msg}
                return {'success': False, 'error': 'Withdrawal failed'}

            logger.info(f"Withdrawal successful for player {player_id}")
            return {'success': True, 'data': data}

        except Exception as e:
            logger.error(f"Withdrawal error: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def deposit_to_player_by_username(self, username, amount, comment="Bot deposit"):
        """Deposit to player by username."""
        player_result = await self.get_players_for_current_agent(username=username)
        if not player_result.get('success'):
            return player_result

        player = player_result.get('player', {})
        player_id = player.get('id') or player.get('playerId')
        if not player_id:
            return {'success': False, 'error': 'Player not found'}

        return await self.deposit_to_player(player_id, amount, comment)

    async def withdraw_from_player_by_username(self, username, amount, comment="Bot withdraw"):
        """Withdraw from player by username."""
        player_result = await self.get_players_for_current_agent(username=username)
        if not player_result.get('success'):
            return player_result

        player = player_result.get('player', {})
        player_id = player.get('id') or player.get('playerId')
        if not player_id:
            return {'success': False, 'error': 'Player not found'}

        return await self.withdraw_from_player(player_id, amount, comment)

    # =============================
    # SYNC COMPATIBILITY LAYER
    # =============================
    # The old API was synchronous. Some callers may still use sync methods.
"""
iChancy API Client - Complete Implementation
Based on: Agent System API Documentation 2026
Features:
  - Automatic token management (signin, refresh, rotation)
  - 403 error handling and recovery
  - Singleton pattern for shared instance
  - All endpoints per PDF specification
"""

import os
import json
import time
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────
BASE_URL = os.getenv("ICHANCY_BASE_URL", "https://www.ichancy.com")
AGENT_EMAIL = os.getenv("ICHANCY_AGENT_EMAIL", "")
AGENT_PASSWORD = os.getenv("ICHANCY_AGENT_PASSWORD", "")

# Token TTL configuration (matching PDF specification)
ACCESS_TOKEN_TTL = 3600        # 1 hour in seconds
REFRESH_TOKEN_TTL = 604800     # 7 days in seconds
TOKEN_REFRESH_BUFFER = 300     # Refresh 5 minutes before expiry

# Retry configuration
MAX_RETRIES = 2
RETRY_DELAY = 1
API_TIMEOUT = 30


class TokenManager:
    """Manages access/refresh tokens with automatic rotation and persistence."""

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_issued_at: Optional[float] = None
        self._token_file = ".ichancy_tokens.json"

        # Attempt to load saved tokens
        self._load_tokens()

    def _load_tokens(self):
        """Load tokens from persistent storage."""
        try:
            if os.path.exists(self._token_file):
                with open(self._token_file, 'r') as f:
                    data = json.load(f)
                    self._access_token = data.get('access_token')
                    self._refresh_token = data.get('refresh_token')
                    self._token_issued_at = data.get('issued_at')
                    logger.info("Loaded saved tokens from file")
        except Exception as e:
            logger.warning(f"Could not load saved tokens: {e}")

    def _save_tokens(self):
        """Save tokens to persistent storage."""
        try:
            with open(self._token_file, 'w') as f:
                json.dump({
                    'access_token': self._access_token,
                    'refresh_token': self._refresh_token,
                    'issued_at': self._token_issued_at
                }, f)
        except Exception as e:
            logger.warning(f"Could not save tokens: {e}")

    @property
    def access_token(self) -> Optional[str]:
        return self._access_token

    @property
    def refresh_token(self) -> Optional[str]:
        return self._refresh_token

    def is_token_valid(self) -> bool:
        """Check if current access token is still valid."""
        if not self._access_token or not self._token_issued_at:
            return False
        elapsed = time.time() - self._token_issued_at
        # Consider token expired if less than buffer remains
        return elapsed < (ACCESS_TOKEN_TTL - TOKEN_REFRESH_BUFFER)

    def is_refresh_token_valid(self) -> bool:
        """Check if refresh token is still valid (7 days)."""
        if not self._refresh_token or not self._token_issued_at:
            return False
        elapsed = time.time() - self._token_issued_at
        return elapsed < (REFRESH_TOKEN_TTL - TOKEN_REFRESH_BUFFER)

    def update_tokens(self, access_token: str, refresh_token: str):
        """Update tokens after signin or refresh."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_issued_at = time.time()
        self._save_tokens()
        logger.info("Tokens updated and saved")

    def clear_tokens(self):
        """Clear all tokens (on auth failure or duplicate signin)."""
        self._access_token = None
        self._refresh_token = None
        self._token_issued_at = None
        if os.path.exists(self._token_file):
            try:
                os.remove(self._token_file)
            except Exception:
                pass
        logger.info("Tokens cleared")


class iChancyAPI:
    """
    iChancy Agent API Client
    Implements all endpoints from the official API documentation.
    """

    _shared = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.email = AGENT_EMAIL
        self.password = AGENT_PASSWORD
        self.token_manager = TokenManager()
        self._session: Optional[aiohttp.ClientSession] = None
        self._auth_in_progress = False

    @classmethod
    def get_shared(cls):
        """Get shared singleton instance."""
        return cls._shared

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "iChancy-Agent-Bot/1.0"
                }
            )
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ═══════════════════════════════════════════════
    # INTERNAL: Request Helpers
    # ═══════════════════════════════════════════════

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        auth_required: bool = True,
        retry_count: int = 0
    ) -> Tuple[bool, Any]:
        """
        Make HTTP request with auth handling and retries.
        Returns: (success, result_or_error)
        """
        url = f"{self.base_url}{endpoint}"
        session = self._get_session()

        request_headers = {}
        if headers:
            request_headers.update(headers)

        # Add auth token if required
        if auth_required:
            if not self.token_manager.is_token_valid():
                if self.token_manager.is_refresh_token_valid():
                    refresh_success = await self._refresh_token()
                    if not refresh_success:
                        # Try full re-auth
                        auth_success = await self._signin()
                        if not auth_success:
                            return False, "Authentication failed - could not obtain valid token"
                else:
                    # No valid refresh token, try signin
                    auth_success = await self._signin()
                    if not auth_success:
                        return False, "Authentication failed - invalid credentials"

            request_headers["Authorization"] = f"Bearer {self.token_manager.access_token}"

        try:
            async with session.request(
                method=method,
                url=url,
                json=data or {},
                headers=request_headers
            ) as response:

                # Handle HTTP 403 Forbidden
                if response.status == 403:
                    error_text = await response.text()
                    logger.error(f"HTTP 403 Forbidden: {endpoint} - {error_text}")

                    # Attempt token refresh on 403 (might be token scope issue)
                    if auth_required and retry_count < MAX_RETRIES:
                        logger.info("Attempting token refresh due to 403")
                        refresh_success = await self._refresh_token()
                        if refresh_success:
                            return await self._make_request(
                                method, endpoint, data, headers,
                                auth_required, retry_count + 1
                            )
                        else:
                            # Try full re-auth
                            auth_success = await self._signin()
                            if auth_success:
                                return await self._make_request(
                                    method, endpoint, data, headers,
                                    auth_required, retry_count + 1
                                )

                    return False, f"HTTP 403 - Forbidden: {error_text}"

                # Handle HTTP 401 Unauthorized
                if response.status == 401:
                    error_text = await response.text()
                    logger.warning(f"HTTP 401 Unauthorized: {endpoint}")

                    if auth_required and retry_count < MAX_RETRIES:
                        # Token might be expired, try refresh
                        refresh_success = await self._refresh_token()
                        if refresh_success:
                            return await self._make_request(
                                method, endpoint, data, headers,
                                auth_required, retry_count + 1
                            )
                        else:
                            # Full re-auth
                            auth_success = await self._signin()
                            if auth_success:
                                return await self._make_request(
                                    method, endpoint, data, headers,
                                    auth_required, retry_count + 1
                                )

                    self.token_manager.clear_tokens()
                    return False, "HTTP 401 - Unauthorized: Token expired or invalid"

                # Parse response
                try:
                    response_data = await response.json()
                except Exception:
                    response_data = {"raw": await response.text()}

                # Check response status field (API envelope)
                if response.status in (200, 201):
                    # API returns status=true even for some errors
                    api_status = response_data.get("status", False)
                    result = response_data.get("result")
                    notifications = response_data.get("notification", [])

                    # Check for error notifications
                    if notifications and len(notifications) > 0:
                        for notif in notifications:
                            if notif.get("status") == "error":
                                error_msg = notif.get("content", "Unknown error")
                                logger.warning(f"API error: {error_msg}")
                                return False, error_msg

                    return True, result if result is not None else response_data

                # HTTP error
                error_detail = response_data.get("notification", [{}])[0].get("content", "Unknown error") if isinstance(response_data.get("notification"), list) else str(response_data)
                logger.error(f"HTTP {response.status}: {error_detail}")
                return False, f"HTTP {response.status}: {error_detail}"

        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {endpoint}")
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
                return await self._make_request(
                    method, endpoint, data, headers,
                    auth_required, retry_count + 1
                )
            return False, "Request timeout"

        except aiohttp.ClientError as e:
            logger.error(f"Connection error: {e}")
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
                return await self._make_request(
                    method, endpoint, data, headers,
                    auth_required, retry_count + 1
                )
            return False, f"Connection error: {str(e)}"

        except Exception as e:
            logger.error(f"Unexpected error in request: {e}")
            return False, f"Request error: {str(e)}"

    # ═══════════════════════════════════════════════
    # AUTHENTICATION
    # ═══════════════════════════════════════════════

    async def _signin(self) -> bool:
        """
        POST /global/api/UserApi/signin
        Authenticate and obtain new token pair.
        """
        if not self.email or not self.password:
            logger.error("Agent email/password not configured")
            return False

        # Prevent concurrent auth attempts
        if self._auth_in_progress:
            # Wait for ongoing auth to complete
            for _ in range(10):
                if not self._auth_in_progress:
                    break
                await asyncio.sleep(0.5)
            return self.token_manager.is_token_valid()

        self._auth_in_progress = True

        try:
            logger.info(f"Signing in as agent: {self.email}")

            success, result = await self._make_request(
                method="POST",
                endpoint="/global/api/UserApi/signin",
                data={
                    "username": self.email,
                    "password": self.password
                },
                auth_required=False
            )

            if success and isinstance(result, dict):
                access_token = result.get("accessToken")
                refresh_token = result.get("refreshToken")

                if access_token and refresh_token:
                    self.token_manager.update_tokens(access_token, refresh_token)
                    logger.info("Signin successful - tokens obtained")

                    # Set as shared instance
                    if iChancyAPI._shared is None:
                        iChancyAPI._shared = self

                    return True

            logger.error(f"Signin failed: {result}")
            return False

        except Exception as e:
            logger.error(f"Signin exception: {e}")
            return False

        finally:
            self._auth_in_progress = False

    async def _refresh_token(self) -> bool:
        """
        POST /global/api/UserApi/refreshToken
        Refresh access token using refresh token.
        """
        refresh_token = self.token_manager.refresh_token
        if not refresh_token:
            logger.warning("No refresh token available")
            return False

        if self._auth_in_progress:
            for _ in range(10):
                if not self._auth_in_progress:
                    break
                await asyncio.sleep(0.5)
            return self.token_manager.is_token_valid()

        self._auth_in_progress = True

        try:
            logger.info("Refreshing access token")

            success, result = await self._make_request(
                method="POST",
                endpoint="/global/api/UserApi/refreshToken",
                data={"refreshToken": refresh_token},
                auth_required=False
            )

            if success and isinstance(result, dict):
                new_access = result.get("accessToken")
                new_refresh = result.get("refreshToken")

                if new_access and new_refresh:
                    self.token_manager.update_tokens(new_access, new_refresh)
                    logger.info("Token refresh successful")
                    return True

            # Refresh failed - clear tokens
            logger.error(f"Token refresh failed: {result}")
            self.token_manager.clear_tokens()
            return False

        except Exception as e:
            logger.error(f"Token refresh exception: {e}")
            self.token_manager.clear_tokens()
            return False

        finally:
            self._auth_in_progress = False

    async def ensure_authenticated(self) -> bool:
        """Ensure we have valid authentication."""
        if self.token_manager.is_token_valid():
            return True
        if self.token_manager.is_refresh_token_valid():
            return await self._refresh_token()
        return await self._signin()

    # ═══════════════════════════════════════════════
    # AGENT ENDPOINTS
    # ═══════════════════════════════════════════════

    async def get_agent_all_wallets(self) -> Dict[str, Any]:
        """
        POST /global/api/UserApi/getAgentAllWallets
        Get agent wallet information.
        """
        success, result = await self._make_request(
            "POST",
            "/global/api/UserApi/getAgentAllWallets",
            data={}
        )
        return {"success": success, "data": result if success else None, "error": None if success else result}

    async def deposit_to_agent(self, amount: float, comment: str, affiliate_id: str, currency_code: str = "NSP") -> Dict[str, Any]:
        """
        POST /global/api/UserApi/depositToAgent
        Deposit to an agent in the agent tree.
        """
        success, result = await self._make_request(
            "POST",
            "/global/api/UserApi/depositToAgent",
            data={
                "amount": float(amount),
                "comment": comment or "",
                "affiliateId": str(affiliate_id),
                "moneyStatus": 3,
                "currencyCode": currency_code
            }
        )
        return {"success": success, "data": result if success else None, "error": None if success else result}

    async def withdraw_from_agent(self, amount: float, comment: str, affiliate_id: str, currency_code: str = "NSP") -> Dict[str, Any]:
        """
        POST /global/api/UserApi/withdrawFromAgent
        Withdraw from an agent in the agent tree.
        Note: amount should be negative for withdrawal.
        """
        success, result = await self._make_request(
            "POST",
            "/global/api/UserApi/withdrawFromAgent",
            data={
                "amount": float(-abs(amount)),
                "comment": comment or "",
                "affiliateId": str(affiliate_id),
                "moneyStatus": 3,
                "currencyCode": currency_code
            }
        )
        return {"success": success, "data": result if success else None, "error": None if success else result}

    async def get_children(self, affiliate_id: Optional[str] = None, start: int = 0, limit: int = 20) -> Dict[str, Any]:
        """
        POST /global/api/UserApi/getChildren
        Get children agents information.
        """
        data = {
            "start": start,
            "limit": limit,
            "filter": {}
        }
        if affiliate_id:
            data["filter"]["affiliateId"] = {
                "action": "=",
                "value": affiliate_id,
                "valueLabel": affiliate_id
            }

        success, result = await self._make_request(
            "POST",
            "/global/api/UserApi/getChildren",
            data=data
        )
        return {"success": success, "data": result if success else None, "error": None if success else result}

    # ═══════════════════════════════════════════════
    # PLAYER ENDPOINTS
    # ═══════════════════════════════════════════════

    async def register_player(self, username: str, password: str, email: str, parent_id: str) -> Dict[str, Any]:
        """
        POST /global/api/UserApi/registerPlayer
        Register a new player account.

        Returns: {"success": bool, "player_id": str|None, "error": str|None}
        """
        # Ensure authenticated first
        auth_ok = await self.ensure_authenticated()
        if not auth_ok:
            return {"success": False, "player_id": None, "error": "Authentication failed"}

        success, result = await self._make_request(
            "POST",
            "/global/api/UserApi/registerPlayer",
            data={
                "player": {
                    "email": email,
                    "password": password,
                    "parentId": str(parent_id),
                    "login": username
                }
            }
        )

        if success:
            # Result is 1 on success
            if result == 1 or result == "1" or result is True:
                return {"success": True, "player_id": None, "error": None}
            else:
                return {"success": True, "player_id": str(result) if result else None, "error": None}
        else:
            return {"success": False, "player_id": None, "error": str(result)}

    async def get_players_for_current_agent(
        self,
        player_id: Optional[str] = None,
        username: Optional[str] = None,
        start: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        POST /global/api/UserApi/getPlayersForCurrentAgent
        Get players for current agent, filtered by playerId or username.
        """
        data = {
            "start": start,
            "limit": limit,
            "filter": {}
        }

        if player_id:
            data["filter"]["playerId"] = {
                "action": "=",
                "value": player_id,
                "valueLabel": player_id
            }
        elif username:
            data["filter"]["userName"] = {
                "action": "=",
                "value": username,
                "valueLabel": username
            }

        success, result = await self._make_request(
            "POST",
            "/global/api/UserApi/getPlayersForCurrentAgent",
            data=data
        )
        return {"success": success, "data": result if success else None, "error": None if success else result}

    async def get_player_id_by_username(self, username: str) -> Optional[str]:
        """
        Get player ID by username (helper using getPlayersForCurrentAgent).

        Returns: player_id string or None
        """
        result = await self.get_players_for_current_agent(username=username)

        if result.get("success") and result.get("data"):
            data = result["data"]
            if isinstance(data, dict) and "records" in data:
                records = data["records"]
                if records and len(records) > 0:
                    return records[0].get("playerId")

        return None

    async def get_player_balance_by_id(self, player_id: str) -> Dict[str, Any]:
        """
        POST /global/api/UserApi/getPlayerBalanceById
        Get player balance by player ID.

        Returns: {"success": bool, "balance": float, "error": str|None}
        """
        success, result = await self._make_request(
            "POST",
            "/global/api/UserApi/getPlayerBalanceById",
            data={"playerId": str(player_id)}
        )

        if success and isinstance(result, list) and len(result) > 0:
            balance_data = result[0]
            return {
                "success": True,
                "balance": float(balance_data.get("balance", 0)),
                "error": None
            }

        return {
            "success": success,
            "balance": 0,
            "error": None if success else str(result)
        }

    async def get_player_balance_by_username(self, username: str) -> Dict[str, Any]:
        """
        Get player balance by username (helper).

        Returns: {"success": bool, "balance": float, "error": str|None}
        """
        # First get player ID
        player_id = await self.get_player_id_by_username(username)

        if not player_id:
            return {"success": False, "balance": 0, "error": f"Player not found: {username}"}

        # Then get balance by ID
        return await self.get_player_balance_by_id(player_id)

    async def deposit_to_player(self, player_id: str, amount: float, comment: str = "", currency_code: str = "NSP") -> Dict[str, Any]:
        """
        POST /global/api/UserApi/depositToPlayer
        Deposit to a player.

        Returns: {"success": bool, "new_balance": float, "error": str|None}
        """
        success, result = await self._make_request(
            "POST",
            "/global/api/UserApi/depositToPlayer",
            data={
                "amount": float(amount),
                "comment": comment or "",
                "playerId": str(player_id),
                "currencyCode": currency_code,
                "currency": currency_code,
                "moneyStatus": 5
            }
        )

        if success and isinstance(result, dict):
            return {
                "success": True,
                "new_balance": float(result.get("balance", 0)),
                "error": None
            }

        return {
            "success": False,
            "new_balance": 0,
            "error": str(result) if not success else "Unknown response"
        }

    async def withdraw_from_player(self, player_id: str, amount: float, comment: str = "", currency_code: str = "NSP") -> Dict[str, Any]:
        """
        POST /global/api/UserApi/withdrawFromPlayer
        Withdraw from a player (amount is positive, sent as negative).

        Returns: {"success": bool, "new_balance": float, "error": str|None}
        """
        success, result = await self._make_request(
            "POST",
            "/global/api/UserApi/withdrawFromPlayer",
            data={
                "amount": float(-abs(amount)),
                "comment": comment or "",
                "playerId": str(player_id),
                "currencyCode": currency_code,
                "currency": currency_code,
                "moneyStatus": 5
            }
        )

        if success and isinstance(result, dict):
            return {
                "success": True,
                "new_balance": float(result.get("balance", 0)),
                "error": None
            }

        return {
            "success": False,
            "new_balance": 0,
            "error": str(result) if not success else "Unknown response"
        }
