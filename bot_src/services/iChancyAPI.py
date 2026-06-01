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

        # Check for manual token first
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
            # Check manual token
            if self.access_token and os.getenv('ICHANCY_ACCESS_TOKEN', '').strip():
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
    # We provide sync wrappers that run the async methods in an event loop.

    def _run_async(self, coro):
        """Run an async coroutine from sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an already-running event loop (e.g., python-telegram-bot)
                # Create a new loop in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result(timeout=120)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def sync_ensure_authenticated(self):
        """Sync wrapper for ensure_authenticated."""
        return self._run_async(self.ensure_authenticated())

    def sync_register_player(self, username, password, email, parent_id=None):
        """Sync wrapper for register_player."""
        return self._run_async(self.register_player(username, password, email, parent_id))

    def sync_get_player_id_by_username(self, username):
        """Sync wrapper for get_player_id_by_username."""
        return self._run_async(self.get_player_id_by_username(username))

    def sync_get_player_balance_by_username(self, username):
        """Sync wrapper for get_player_balance_by_username."""
        return self._run_async(self.get_player_balance_by_username(username))

    def sync_deposit_to_player_by_username(self, username, amount, comment="Bot deposit"):
        """Sync wrapper for deposit_to_player_by_username."""
        return self._run_async(self.deposit_to_player_by_username(username, amount, comment))

    def sync_withdraw_from_player_by_username(self, username, amount, comment="Bot withdraw"):
        """Sync wrapper for withdraw_from_player_by_username."""
        return self._run_async(self.withdraw_from_player_by_username(username, amount, comment))

    # Legacy sync method names for backward compatibility
    # These will be called by code that hasn't been updated to async yet
    def _ensure_authenticated(self):
        """Legacy sync auth - triggers browser sign-in via thread."""
        return self.sync_ensure_authenticated()

    def register_player_sync(self, username, password, email, parent_id=None):
        """Legacy sync register_player."""
        return self.sync_register_player(username, password, email, parent_id)
