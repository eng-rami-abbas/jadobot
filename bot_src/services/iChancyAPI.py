"""
iChancy Agent API Client - OPTIMIZED VERSION
============================================
Key improvements over the original:
1. Direct token authentication (NO Playwright needed if token is set)
2. Extended TTL (6 hours instead of 30 minutes)
3. Smart 403 handling (retry once, don't reset instance)
4. httpx-only with connection pooling (removed requests fallback)
5. Exponential backoff for retries
6. Cached browser cookies (class-level reuse)
7. Proper resource cleanup
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try importing Playwright (fallback only)
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

# HTTP client - httpx only (removed requests fallback)
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    raise RuntimeError("httpx is required. Install with: pip install httpx")


class iChancyAPI:
    """
    OPTIMIZED iChancy Agent API client.

    Priority authentication methods:
      1. Direct token (ICHANCY_ACCESS_TOKEN env var) - FASTEST
      2. Browser-based (Playwright) - SLOW, fallback only
    """

    BASE_URL = 'https://agents.ichancy.com'
    API_BASE = f'{BASE_URL}/global/api'

    # ==== CONFIGURATION (tune these) ====
    # Extended from 30 minutes to 6 hours
    _auth_ttl = timedelta(hours=6)
    # Retry configuration
    _max_retries = 2
    _retry_base_delay = 1.0  # seconds
    # =====================================

    # Singleton-like shared session
    _shared_instance = None
    _last_auth_time = None

    # Cached browser cookies (class-level for reuse)
    _browser_cookies = None

    @classmethod
    def get_shared(cls):
        """Get or create a shared API instance."""
        now = datetime.now()
        if cls._shared_instance is None:
            logger.info("Creating new shared iChancyAPI instance")
            cls._shared_instance = cls()
            cls._last_auth_time = now
        elif cls._last_auth_time and now - cls._last_auth_time > cls._auth_ttl:
            logger.info("Auth TTL expired, creating fresh instance")
            # Clean up old instance
            old = cls._shared_instance
            cls._shared_instance = cls()
            cls._last_auth_time = now
            # Schedule cleanup of old client
            asyncio.create_task(old._cleanup())
        return cls._shared_instance

    @classmethod
    def reset_shared(cls):
        """Reset the shared instance to force re-authentication."""
        logger.info("Resetting shared iChancyAPI instance")
        if cls._shared_instance:
            old = cls._shared_instance
            cls._shared_instance = None
            cls._last_auth_time = None
            cls._browser_cookies = None
            asyncio.create_task(old._cleanup())

    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.agent_id = None
        self._http_client = None
        self._authenticated = False
        self._auth_attempts = 0
        self._max_auth_attempts = 3

        # Check for direct token FIRST (fastest path)
        manual_token = os.getenv('ICHANCY_ACCESS_TOKEN', '').strip()
        if manual_token:
            self.access_token = manual_token
            self.token_expires_at = datetime.now() + timedelta(hours=24)
            self._authenticated = True
            logger.info("Using ICHANCY_ACCESS_TOKEN - Playwright NOT needed")
        else:
            logger.warning("No ICHANCY_ACCESS_TOKEN set - will need Playwright fallback")

        # Initialize HTTP client with connection pooling
        self._init_http_client()

    def _init_http_client(self):
        """Initialize the HTTP client with connection pooling."""
        if HAS_HTTPX:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=60.0
                ),
                http2=False,  # HTTP/1.1 is more compatible
            )
            logger.debug("httpx AsyncClient initialized with connection pooling")
        else:
            raise RuntimeError("httpx is required for iChancyAPI")

    async def _cleanup(self):
        """Clean up resources (http client)."""
        try:
            if self._http_client:
                await self._http_client.aclose()
                logger.debug("HTTP client closed")
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
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

    async def _api_post(self, url, payload, timeout=30):
        """Make an async POST request to the iChancy API with retry logic."""
        headers = await self._get_headers(with_auth=True)
        cookies = await self._get_cookies_dict()

        last_exception = None
        for attempt in range(self._max_retries):
            try:
                response = await self._http_client.post(
                    url,
                    json=payload,
                    headers=headers,
                    cookies=cookies,
                    timeout=timeout,
                )

                # If 403, retry once without resetting instance
                if response.status_code == 403 and attempt < self._max_retries - 1:
                    logger.warning(f"Got 403 on POST {url}, retrying (attempt {attempt + 1})...")
                    delay = self._retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue

                return response

            except httpx.TimeoutException as e:
                logger.warning(f"POST timeout (attempt {attempt + 1}): {e}")
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"POST error (attempt {attempt + 1}): {e}")
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

        # All retries exhausted
        if last_exception:
            raise last_exception

        # Create a dummy response for error cases
        class DummyResponse:
            status_code = 0
            def json(self):
                return {}
            def text(self):
                return ""
        return DummyResponse()

    async def _api_get(self, url, timeout=30):
        """Make an async GET request to the iChancy API with retry logic."""
        headers = await self._get_headers(with_auth=True)
        cookies = await self._get_cookies_dict()

        last_exception = None
        for attempt in range(self._max_retries):
            try:
                response = await self._http_client.get(
                    url,
                    headers=headers,
                    cookies=cookies,
                    timeout=timeout,
                )

                if response.status_code == 403 and attempt < self._max_retries - 1:
                    logger.warning(f"Got 403 on GET {url}, retrying (attempt {attempt + 1})...")
                    delay = self._retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue

                return response

            except httpx.TimeoutException as e:
                logger.warning(f"GET timeout (attempt {attempt + 1}): {e}")
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"GET error (attempt {attempt + 1}): {e}")
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

        if last_exception:
            raise last_exception

        class DummyResponse:
            status_code = 0
            def json(self):
                return {}
        return DummyResponse()

    # =============================
    # BROWSER-BASED AUTHENTICATION (FALLBACK ONLY)
    # =============================
    async def _wait_for_cloudflare_challenge(self, page, max_wait=15):
        """
        Wait for Cloudflare challenge/turnstile to resolve.
        REDUCED from 30s to 15s max wait.
        """
        try:
            for i in range(max_wait):
                page_title = await page.title()
                current_url = page.url

                if any(indicator in page_title.lower() for indicator in
                       ['just a moment', 'attention required', 'checking', 'cloudflare']):
                    logger.info(f"Cloudflare challenge detected (title: {page_title}), waiting... ({i+1}/{max_wait})")
                    await page.wait_for_timeout(1000)  # Reduced from 2000ms
                    continue

                challenge_el = await page.query_selector(
                    '#challenge-running, .cf-browser-verification, #cf-challenge-running, '
                    'iframe[src*="challenges.cloudflare.com"]'
                )
                if challenge_el:
                    logger.info(f"Cloudflare element found, waiting... ({i+1}/{max_wait})")
                    await page.wait_for_timeout(1000)
                    continue

                break

            await page.wait_for_timeout(1000)  # Reduced from 2000ms

        except Exception as e:
            logger.warning(f"Error during Cloudflare challenge wait: {e}")

    async def _browser_signin(self, username, password):
        """
        OPTIMIZED browser sign-in.
        Uses faster timeouts and reduced wait times.
        """
        if not HAS_PLAYWRIGHT:
            logger.error("Playwright not available for browser-based sign-in")
            return False

        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(
                    headless=True,
                    # Performance optimizations
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )

                context = await browser.new_context(
                    viewport={"width": 1366, "height": 768},  # Reduced from 1920x1080
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
                    locale="en-US",
                    java_script_enabled=True,
                )

                page = await context.new_page()

                if HAS_STEALTH:
                    await stealth_async(page)

                # Navigate to login page - FASTER timeout
                logger.info(f"Navigating to {self.BASE_URL}/login...")
                try:
                    await page.goto(
                        f"{self.BASE_URL}/login",
                        wait_until="domcontentloaded",
                        timeout=30000  # Reduced from 60000
                    )
                except Exception as nav_err:
                    logger.warning(f"Navigation timeout: {nav_err}")
                    await browser.close()
                    return False

                # Wait for Cloudflare (REDUCED wait)
                await self._wait_for_cloudflare_challenge(page, max_wait=10)

                # Wait for SPA to render (REDUCED)
                await page.wait_for_timeout(2000)  # Reduced from 3000

                # Try networkidle with shorter timeout
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass

                # Find and fill username field
                username_selectors = [
                    'input[name="username"]',
                    'input[type="email"]',
                    'input[id*="user" i]',
                    'input[id*="email" i]',
                    'input[autocomplete="username"]',
                    'input[autocomplete="email"]',
                ]

                username_filled = False
                username_element = None

                for selector in username_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=2000)
                        if element:
                            username_element = element
                            break
                    except Exception:
                        continue

                # Fallback: find any visible input
                if not username_element:
                    try:
                        all_inputs = await page.query_selector_all('input')
                        for inp in all_inputs:
                            try:
                                inp_type = await inp.get_attribute('type') or ''
                                if inp_type not in ('password', 'hidden', 'submit'):
                                    if await inp.is_visible():
                                        username_element = inp
                                        break
                            except Exception:
                                continue
                    except Exception:
                        pass

                if username_element:
                    try:
                        await username_element.click()
                        await username_element.fill(username)
                        username_filled = True
                        logger.info("Filled username field")
                    except Exception as e:
                        logger.error(f"Error filling username: {e}")

                if not username_filled:
                    logger.error("Could not find username field")
                    await browser.close()
                    return False

                # Find and fill password field
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[autocomplete="current-password"]',
                ]

                password_filled = False
                password_element = None

                for selector in password_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=2000)
                        if element:
                            password_element = element
                            break
                    except Exception:
                        continue

                if password_element:
                    try:
                        await password_element.click()
                        await password_element.fill(password)
                        password_filled = True
                        logger.info("Filled password field")
                    except Exception as e:
                        logger.error(f"Error filling password: {e}")

                if not password_filled:
                    logger.error("Could not find password field")
                    await browser.close()
                    return False

                # Click submit button
                submit_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Log in")',
                    'button:has-text("Sign in")',
                ]

                submitted = False
                for selector in submit_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=2000)
                        if element:
                            await element.click()
                            submitted = True
                            logger.info(f"Clicked submit: {selector}")
                            break
                    except Exception:
                        continue

                if not submitted:
                    # Fallback: find any submit-like button
                    try:
                        buttons = await page.query_selector_all('button')
                        for btn in buttons:
                            try:
                                btn_text = await btn.text_content() or ''
                                if await btn.is_visible() and any(kw in btn_text.lower()
                                                                    for kw in ['login', 'sign in', 'submit']):
                                    await btn.click()
                                    submitted = True
                                    logger.info(f"Clicked fallback submit button")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                if not submitted:
                    logger.error("Could not find submit button")
                    await browser.close()
                    return False

                # Wait for navigation (REDUCED)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass

                await page.wait_for_timeout(3000)  # Reduced from 5000

                # Extract token from localStorage
                token_data = await page.evaluate("""() => {
                    return {
                        accessToken: localStorage.getItem('accessToken') || localStorage.getItem('token'),
                        refreshToken: localStorage.getItem('refreshToken'),
                        allKeys: Object.keys(localStorage)
                    };
                }""")

                self.access_token = token_data.get("accessToken")
                self.refresh_token = token_data.get("refreshToken")

                # Fallback: try sessionStorage
                if not self.access_token:
                    session_data = await page.evaluate("""() => {
                        return {
                            accessToken: sessionStorage.getItem('accessToken') || sessionStorage.getItem('token'),
                            refreshToken: sessionStorage.getItem('refreshToken'),
                            allKeys: Object.keys(sessionStorage)
                        };
                    }""")
                    if session_data.get('accessToken'):
                        self.access_token = session_data['accessToken']
                        self.refresh_token = self.refresh_token or session_data.get('refreshToken')

                # Fallback: try cookies
                if not self.access_token:
                    cookies = await context.cookies()
                    for cookie in cookies:
                        if 'token' in cookie.get('name', '').lower():
                            self.access_token = cookie.get('value')
                            logger.info(f"Found token in cookie: {cookie.get('name')}")
                            break

                # Extract cookies for reuse
                iChancyAPI._browser_cookies = await context.cookies()

                await browser.close()
                browser = None

                if self.access_token:
                    self.token_expires_at = datetime.now() + timedelta(hours=6)  # Extended
                    self._authenticated = True
                    logger.info("Browser sign-in successful - token obtained")
                    iChancyAPI._last_auth_time = datetime.now()
                    return True
                else:
                    logger.error("No access token found after browser sign-in")
                    return False

        except Exception as e:
            logger.error(f"Browser sign-in error: {e}", exc_info=True)
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            return False

    # =============================
    # AUTHENTICATION (OPTIMIZED)
    # =============================
    async def ensure_authenticated(self):
        """Ensure we have a valid access token. Uses direct token first, browser fallback."""
        try:
            # Priority 1: Direct token from env (fastest)
            if self.access_token and os.getenv('ICHANCY_ACCESS_TOKEN', '').strip():
                return True

            # Priority 2: Check cached token expiry
            if self.access_token and not self._is_token_expired():
                return True

            # Priority 3: Re-authenticate (browser fallback)
            if self._auth_attempts < self._max_auth_attempts:
                self._auth_attempts += 1
                logger.info(f"Re-authenticating (attempt {self._auth_attempts}/{self._max_auth_attempts})...")
                result = await self._do_signin()
                if result:
                    self._auth_attempts = 0  # Reset on success
                return result
            else:
                logger.error(f"Max auth attempts ({self._max_auth_attempts}) reached")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return False

    async def _do_signin(self):
        """Perform sign-in using the best available method."""
        username = os.getenv('ICHANCY_USERNAME', '').strip()
        password = os.getenv('ICHANCY_PASSWORD', '').strip()

        if not username or not password:
            try:
                import config.telegram as cfg
                username = username or getattr(cfg, 'ICHANCY_USERNAME', '')
                password = password or getattr(cfg, 'ICHANCY_PASSWORD', '')
            except Exception:
                pass

        if not username or not password:
            logger.error("MISSING iChancy credentials (ICHANCY_USERNAME / ICHANCY_PASSWORD)")
            return False

        # Try direct API sign-in FIRST (faster than browser)
        logger.info("Trying direct API sign-in...")
        if await self._direct_api_signin(username, password):
            return True

        # Fallback: browser-based sign-in
        if HAS_PLAYWRIGHT:
            logger.info("Falling back to browser-based sign-in...")
            for attempt in range(2):
                try:
                    success = await self._browser_signin(username, password)
                    if success:
                        return True
                    logger.warning(f"Browser sign-in attempt {attempt + 1} failed")
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Browser sign-in attempt {attempt + 1} error: {e}")
                    await asyncio.sleep(2)

        logger.error("All sign-in methods failed")
        return False

    async def _direct_api_signin(self, username, password):
        """Direct API sign-in without browser (faster path)."""
        try:
            url = f"{self.API_BASE}/UserApi/signin"
            payload = {"username": username, "password": password}

            headers = {
                'Content-Type': 'application/json',
                'Origin': self.BASE_URL,
                'Referer': self.BASE_URL + '/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
            }

            response = await self._http_client.post(url, json=payload, headers=headers, timeout=15)
            status = response.status_code

            if status == 403:
                logger.warning("Direct API sign-in blocked by Cloudflare (403)")
                return False

            if status != 200:
                logger.error(f"Direct API sign-in failed: HTTP {status}")
                return False

            try:
                data = response.json()
            except Exception:
                logger.error("Invalid JSON in sign-in response")
                return False

            if not data.get('status'):
                logger.error("API sign-in returned status=false")
                return False

            result = data.get('result', {})
            self.access_token = result.get('accessToken')
            self.refresh_token = result.get('refreshToken')

            if self.access_token:
                self.token_expires_at = datetime.now() + timedelta(hours=6)  # Extended
                self._authenticated = True
                logger.info("Direct API sign-in successful")
                iChancyAPI._last_auth_time = datetime.now()
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

            response = await self._api_post(url, payload, timeout=30)
            status = response.status_code if hasattr(response, 'status_code') else 0

            if status == 403:
                logger.warning("Got 403 on register, retrying once...")
                response = await self._api_post(url, payload, timeout=30)
                status = response.status_code if hasattr(response, 'status_code') else 0
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

    def _run_async(self, coro):
        """Run an async coroutine from sync context - OPTIMIZED."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Submit to the running loop more efficiently
                future = asyncio.run_coroutine_threadsafe(coro, loop)
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
    def _ensure_authenticated(self):
        """Legacy sync auth."""
        return self.sync_ensure_authenticated()

    def register_player_sync(self, username, password, email, parent_id=None):
        """Legacy sync register_player."""
        return self.sync_register_player(username, password, email, parent_id)
