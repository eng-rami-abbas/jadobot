"""
iChancy Agent API Client
========================
Connects to agents.ichancy.com API with Cloudflare bypass.
Uses multiple strategies with session recycling:
  1. curl_cffi (best TLS fingerprint impersonation)
  2. cloudscraper (Cloudflare challenge solver)
  3. requests with browser headers
  4. raw requests with minimal headers (last resort)

On 403: destroys the entire session, rebuilds with the next
available strategy, and retries.
"""

import os
import json
import time
import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try cloudscraper first, fall back to requests
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

try:
    import requests as raw_requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

# ---------------------------------------------------------------------------
# Browser-impersonation profiles we cycle through when a 403 forces a rebuild.
# Newer Chrome versions first, then Firefox as a fallback.
# ---------------------------------------------------------------------------
_CURL_IMPERSONATE_PROFILES = [
    "chrome124",
    "chrome120",
    "chrome119",
    "chrome116",
    "chrome110",
    "chrome107",
    "chrome104",
    "chrome101",
    "chrome100",
    "edge101",
    "safari17_0",
    "safari15_5",
    "safari15_3",
]

_CLOUDSCRAPER_BROWSERS = [
    {"browser": "chrome", "platform": "windows", "mobile": False},
    {"browser": "chrome", "platform": "darwin", "mobile": False},
    {"browser": "firefox", "platform": "windows", "mobile": False},
]


def _is_cloudflare_block(response):
    """Return True if the response looks like a Cloudflare block page.

    Cloudflare can respond with:
      - An HTML challenge page (status 403 or 503)
      - A JSON body containing ``cf-mitigated`` or ``cf_chl_rc``
      - Response headers like ``cf-mitigated: challenge``
    """
    status = getattr(response, 'status_code', 0)
    if status not in (403, 503):
        return False

    # Check response headers
    resp_headers = getattr(response, 'headers', {})
    if resp_headers.get('cf-mitigated'):
        return True
    if resp_headers.get('server', '').lower().startswith('cloudflare'):
        # Cloudflare server header + 403/503 is very likely a block
        pass  # still check body below

    # Check body
    text = ''
    try:
        text = getattr(response, 'text', '') or ''
    except Exception:
        pass

    text_lower = text.lower()

    # Classic HTML challenge page
    if '<!doctype' in text_lower or '<html' in text_lower:
        if 'cloudflare' in text_lower or 'cf-' in text_lower or 'challenge' in text_lower:
            return True
        # Any HTML on a 403 from an API endpoint is suspicious
        if len(text) > 200:
            return True

    # JSON Cloudflare responses
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            # Cloudflare mitigation markers in JSON
            if data.get('cf-mitigated') or data.get('cf_chl_rc'):
                return True
            if 'cloudflare' in str(data.get('message', '')).lower():
                return True
    except (json.JSONDecodeError, ValueError):
        pass

    # Short HTML fragments like "<html><body>403</body></html>"
    if text_lower.strip().startswith('<') and status == 403:
        return True

    return False


class iChancyAPI:
    """
    iChancy Agent API client with robust Cloudflare bypass.

    Strategy priority:
      1. curl_cffi  – full TLS fingerprint impersonation
      2. cloudscraper – JS challenge solver
      3. requests + browser headers
      4. raw requests + minimal headers (sometimes over-engineered
         headers themselves trigger CF)

    On every 403 the session is completely torn down and rebuilt
    with the next available strategy.  Cookies from a successful
    sign-in are persisted and injected into new sessions so we
    survive longer without re-authenticating.
    """

    BASE_URL = 'https://agents.ichancy.com'
    API_BASE = f'{BASE_URL}/global/api'

    # Singleton-like shared session to avoid re-authenticating on every call
    _shared_instance = None
    _last_auth_time = None
    _auth_ttl = timedelta(minutes=30)

    # Persisted cookies from a successful sign-in (class-level so they
    # survive session rebuilds)
    _persisted_cookies = None

    @classmethod
    def get_shared(cls):
        """Get or create a shared API instance to avoid re-authentication overhead."""
        now = datetime.now()
        if cls._shared_instance is None or (cls._last_auth_time and now - cls._last_auth_time > cls._auth_ttl):
            try:
                cls._shared_instance = cls()
                cls._last_auth_time = now
            except Exception as e:
                logger.warning(f"Failed to create shared API instance: {e}")
                cls._shared_instance = None
        return cls._shared_instance

    def __init__(self):
        self.session = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.agent_id = None
        self._session_type = None
        self._strategy_index = 0        # which strategy we're on
        self._curl_profile_index = 0    # which curl_cffi profile
        self._cs_browser_index = 0      # which cloudscraper browser config

        # Setup session with best available strategy
        self._init_session()

        # Auto login
        self._ensure_authenticated()

    # ------------------------------------------------------------------
    # SESSION MANAGEMENT
    # ------------------------------------------------------------------
    def _init_session(self):
        """Initialize HTTP session with best available strategy.

        Strategies (in order):
          0 – curl_cffi
          1 – cloudscraper
          2 – requests + browser headers
          3 – raw requests + minimal headers
        """
        self._destroy_session()

        # Strategy 0: curl_cffi (best Cloudflare bypass via TLS fingerprint)
        if self._strategy_index == 0 and HAS_CURL_CFFI:
            try:
                profile = _CURL_IMPERSONATE_PROFILES[
                    self._curl_profile_index % len(_CURL_IMPERSONATE_PROFILES)
                ]
                self.session = curl_requests.Session(impersonate=profile)
                self._session_type = "curl_cffi"
                logger.info(f"Using curl_cffi session (impersonate={profile})")
                self._inject_persisted_cookies()
                return
            except Exception as e:
                logger.warning(f"curl_cffi init failed: {e}")
                self._strategy_index += 1  # fall through to next

        # Strategy 1: cloudscraper
        if self._strategy_index <= 1 and HAS_CLOUDSCRAPER:
            try:
                browser_cfg = _CLOUDSCRAPER_BROWSERS[
                    self._cs_browser_index % len(_CLOUDSCRAPER_BROWSERS)
                ]
                self.session = cloudscraper.create_scraper(browser=browser_cfg)
                self._session_type = "cloudscraper"
                logger.info(f"Using cloudscraper session (browser={browser_cfg})")
                self._inject_persisted_cookies()
                return
            except Exception as e:
                logger.warning(f"cloudscraper init failed: {e}")
                self._strategy_index += 1

        # Strategy 2: plain requests with browser headers
        if self._strategy_index <= 2 and HAS_REQUESTS:
            self.session = raw_requests.Session()
            self._session_type = "requests"
            logger.info("Using plain requests session with browser headers")
            self._inject_persisted_cookies()
            return

        # Strategy 3: raw requests with minimal headers
        if self._strategy_index <= 3 and HAS_REQUESTS:
            self.session = raw_requests.Session()
            self._session_type = "raw_requests"
            logger.info("Using raw requests session with minimal headers")
            self._inject_persisted_cookies()
            return

        raise RuntimeError("No HTTP library available (need requests, cloudscraper, or curl_cffi)")

    def _destroy_session(self):
        """Completely tear down the current session."""
        if self.session is not None:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = None
        self._session_type = None

    def _rebuild_session(self):
        """Destroy session, advance to next strategy/profile, and rebuild."""
        self._destroy_session()

        if self._session_type == "curl_cffi" or self._strategy_index == 0:
            # Try next curl profile first
            self._curl_profile_index += 1
            if self._curl_profile_index < len(_CURL_IMPERSONATE_PROFILES):
                self._strategy_index = 0  # stay on curl_cffi
                logger.info(f"Retrying with next curl_cffi profile (index {self._curl_profile_index})")
            else:
                # Exhausted curl profiles, move to cloudscraper
                self._strategy_index = 1
                logger.info("Exhausted curl_cffi profiles, trying cloudscraper")
        elif self._session_type == "cloudscraper" or self._strategy_index == 1:
            # Try next cloudscraper browser config
            self._cs_browser_index += 1
            if self._cs_browser_index < len(_CLOUDSCRAPER_BROWSERS):
                self._strategy_index = 1  # stay on cloudscraper
                logger.info(f"Retrying with next cloudscraper config (index {self._cs_browser_index})")
            else:
                self._strategy_index = 2
                logger.info("Exhausted cloudscraper configs, trying plain requests")
        else:
            # Advance to the next strategy
            self._strategy_index = min(self._strategy_index + 1, 3)

        self._init_session()

    def _inject_persisted_cookies(self):
        """Inject any previously saved cookies into the current session."""
        if not iChancyAPI._persisted_cookies or not self.session:
            return
        try:
            if hasattr(self.session, 'cookies'):
                for name, value in iChancyAPI._persisted_cookies.items():
                    self.session.cookies.set(name, value, domain='agents.ichancy.com')
                logger.debug(f"Injected {len(iChancyAPI._persisted_cookies)} persisted cookies")
        except Exception as e:
            logger.warning(f"Failed to inject persisted cookies: {e}")

    def _persist_cookies(self):
        """Save current session cookies for future session rebuilds."""
        if not self.session:
            return
        try:
            cookies = {}
            if hasattr(self.session, 'cookies'):
                for cookie in self.session.cookies:
                    cookies[cookie.name] = cookie.value
            if cookies:
                iChancyAPI._persisted_cookies = cookies
                logger.debug(f"Persisted {len(cookies)} cookies for session reuse")
        except Exception as e:
            logger.warning(f"Failed to persist cookies: {e}")

    # ------------------------------------------------------------------
    # HEADERS
    # ------------------------------------------------------------------
    def _get_headers(self, with_auth=False):
        """Return a headers dict appropriate for the current session type.

        - For ``raw_requests`` we send *minimal* headers because
          over-engineered headers can themselves trigger Cloudflare.
        - For ``curl_cffi`` we let the impersonation engine set most
          headers automatically and only add what the API requires.
        - For other session types we send full browser-like headers.
        """
        if self._session_type == "raw_requests":
            # Minimal headers – sometimes less is more with CF
            h = {
                'Content-Type': 'application/json',
                'Origin': self.BASE_URL,
                'Referer': self.BASE_URL + '/',
            }
            if with_auth and self.access_token:
                h['Authorization'] = f'Bearer {self.access_token}'
            return h

        if self._session_type == "curl_cffi":
            # curl_cffi handles UA, Accept-Encoding, sec-ch-ua etc. via
            # impersonation.  We only add what the iChancy API expects.
            h = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': self.BASE_URL,
                'Referer': self.BASE_URL + '/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
            if with_auth and self.access_token:
                h['Authorization'] = f'Bearer {self.access_token}'
            return h

        # cloudscraper / plain requests – full browser headers
        h = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'Origin': self.BASE_URL,
            'Referer': self.BASE_URL + '/',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="125", "Chromium";v="125"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Connection': 'keep-alive',
        }
        if with_auth and self.access_token:
            h['Authorization'] = f'Bearer {self.access_token}'
        return h

    # ------------------------------------------------------------------
    # HTTP VERBS
    # ------------------------------------------------------------------
    def _post(self, url, payload, timeout=30):
        """Make a POST request with the current session."""
        with_auth = bool(self.access_token)
        headers = self._get_headers(with_auth=with_auth)

        logger.debug(f"POST {url} (session type: {self._session_type})")

        if self._session_type == "curl_cffi":
            return self.session.post(url, json=payload, headers=headers, timeout=timeout)
        else:
            return self.session.post(url, json=payload, headers=headers, timeout=timeout)

    def _get(self, url, timeout=30):
        """Make a GET request with the current session."""
        with_auth = bool(self.access_token)
        headers = self._get_headers(with_auth=with_auth)

        if self._session_type == "curl_cffi":
            return self.session.get(url, headers=headers, timeout=timeout)
        else:
            return self.session.get(url, headers=headers, timeout=timeout)

    # ------------------------------------------------------------------
    # 403 RECOVERY
    # ------------------------------------------------------------------
    def _handle_403(self, response, context="request"):
        """Handle a 403 by rebuilding the session with a fresh strategy.

        Returns True if the session was rebuilt (caller should retry),
        False if we've exhausted all strategies.
        """
        is_cf = _is_cloudflare_block(response)

        if is_cf:
            logger.warning(f"Cloudflare block detected during {context}")
        else:
            # Non-Cloudflare 403 – could be API-level permission issue
            text = getattr(response, 'text', '')[:300]
            logger.warning(f"403 Forbidden (not Cloudflare) during {context}: {text}")
            # Still try a session rebuild – sometimes stale cookies cause this
            # but also try clearing auth state
            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None

        # Check if we still have strategies to try
        max_strategy = 3  # raw_requests is the last
        if self._strategy_index >= max_strategy and self._session_type == "raw_requests":
            # Already on last strategy and still failing
            logger.error("All session strategies exhausted – cannot bypass 403")
            # Reset strategy index so the next attempt starts fresh
            self._strategy_index = 0
            self._curl_profile_index = 0
            self._cs_browser_index = 0
            return False

        # Rebuild with next strategy
        self._rebuild_session()
        return True

    # =============================
    # AUTHENTICATION
    # =============================
    def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        try:
            if not self.access_token or self._is_token_expired():
                if self.refresh_token and not self._is_refresh_expired():
                    logger.info("Token expired, attempting refresh...")
                    if not self._refresh_token():
                        logger.info("Refresh failed, performing new sign-in...")
                        self._sign_in()
                else:
                    logger.info("No valid tokens, performing sign-in...")
                    self._sign_in()

            if self.access_token:
                return True
            else:
                logger.error("Failed to obtain access token")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return False

    def _is_token_expired(self):
        if not self.token_expires_at:
            return True
        return datetime.now() >= self.token_expires_at

    def _is_refresh_expired(self):
        # Refresh tokens last 7 days
        return False

    def _sign_in(self):
        """Sign in to iChancy API with multi-strategy retry logic.

        On 403 the entire session is torn down and rebuilt with the next
        available TLS-fingerprint / strategy.  We cycle through all
        strategies before giving up.
        """
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

        url = f"{self.API_BASE}/UserApi/signin"
        payload = {
            "username": username,
            "password": password
        }

        max_retries = 6  # More retries to cycle through strategies
        for attempt in range(max_retries):
            try:
                logger.info(f"Sign-in attempt {attempt + 1}/{max_retries} (strategy: {self._session_type})...")

                # Small random jitter to avoid looking robotic
                if attempt > 0:
                    jitter = random.uniform(1.0, 3.0)
                    time.sleep(2 * attempt + jitter)

                response = self._post(url, payload, timeout=45)
                status = getattr(response, 'status_code', 0)

                logger.info(f"Sign-in response status: {status} (strategy: {self._session_type})")

                # ---- 403 handling ----
                if status == 403:
                    can_retry = self._handle_403(response, context="sign-in")
                    if can_retry and attempt < max_retries - 1:
                        continue
                    else:
                        logger.error("All sign-in attempts blocked (403)")
                        return False

                # ---- 503 handling (Cloudflare challenge page) ----
                if status == 503:
                    if _is_cloudflare_block(response):
                        logger.warning(f"Cloudflare 503 challenge (attempt {attempt + 1})")
                        can_retry = self._handle_403(response, context="sign-in-503")
                        if can_retry and attempt < max_retries - 1:
                            continue
                        return False
                    logger.error(f"503 Service Unavailable (not Cloudflare)")
                    if attempt < max_retries - 1:
                        continue
                    return False

                # ---- API-level auth failure (docs say 201 = unauthorized) ----
                if status == 201:
                    logger.error("Sign-in failed: API returned 201 (unauthorized) – check credentials")
                    return False

                if status == 401:
                    logger.error("Sign-in failed: 401 Unauthorized – check credentials")
                    return False

                if status != 200:
                    logger.error(f"Sign-in failed with HTTP {status}")
                    resp_text = getattr(response, 'text', '')[:500]
                    logger.error(f"Response: {resp_text}")
                    if attempt < max_retries - 1:
                        # Rebuild session on any unexpected error
                        self._rebuild_session()
                        continue
                    return False

                # ---- Parse JSON response ----
                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"Failed to parse sign-in response: {e}")
                    text = getattr(response, 'text', '')[:200]
                    logger.error(f"Response text: {text}")
                    if attempt < max_retries - 1:
                        self._rebuild_session()
                        continue
                    return False

                if not data.get('status'):
                    logger.error("API returned status=false")
                    notifications = data.get('notification', [])
                    if notifications:
                        error_msg = notifications[0].get('content', 'Unknown error')
                        logger.error(f"Error: {error_msg}")
                    return False

                result = data.get('result')
                if not result:
                    logger.error("Sign-in returned no result")
                    return False

                self.access_token = result.get('accessToken')
                self.refresh_token = result.get('refreshToken')

                if not self.access_token:
                    logger.error("No access token received from sign-in")
                    return False

                # Set token expiration (1 hour)
                self.token_expires_at = datetime.now() + timedelta(hours=1)

                # Persist cookies from this session for future reuse
                self._persist_cookies()

                logger.info("Successfully signed in to iChancy API")
                iChancyAPI._last_auth_time = datetime.now()

                # Reset strategy indices so the next auth cycle starts fresh
                self._curl_profile_index = 0
                self._cs_browser_index = 0

                return True

            except Exception as e:
                logger.error(f"Sign-in exception (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    self._rebuild_session()
                else:
                    return False

        return False

    def _refresh_token(self):
        """Refresh access token using refresh token."""
        try:
            url = f"{self.API_BASE}/UserApi/refreshToken"
            payload = {"refreshToken": self.refresh_token}

            logger.info("Refreshing iChancy API token...")
            response = self._post(url, payload, timeout=30)

            status = getattr(response, 'status_code', 0)

            if status == 403:
                can_retry = self._handle_403(response, context="token-refresh")
                if can_retry:
                    # Retry the refresh with new session
                    try:
                        response = self._post(url, payload, timeout=30)
                        status = getattr(response, 'status_code', 0)
                    except Exception as e:
                        logger.error(f"Token refresh retry failed: {e}")
                        return self._sign_in()

            if status != 200:
                logger.warning("Token refresh failed, will sign in again")
                return self._sign_in()

            try:
                data = response.json()
            except Exception:
                logger.error("Invalid JSON from token refresh")
                return False

            if not data.get('status') or not data.get('result'):
                return self._sign_in()

            result = data['result']
            self.access_token = result.get('accessToken')
            self.refresh_token = result.get('refreshToken')
            self.token_expires_at = datetime.now() + timedelta(hours=1)

            # Persist cookies
            self._persist_cookies()

            logger.info("Successfully refreshed token")
            return True

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False

    # =============================
    # PLAYER MANAGEMENT
    # =============================
    def register_player(self, username, password, email, parent_id=None):
        """Register a new player using the official API."""
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'فشل في المصادقة مع خوادم iChancy - يرجى المحاولة لاحقاً'}

        try:
            url = f"{self.API_BASE}/UserApi/registerPlayer"

            if not parent_id:
                parent_id = os.getenv('ICHANCY_PARENT_ID', '2613607')
                # Also check PARENT_ID env var
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

            response = self._post(url, payload, timeout=30)
            status = getattr(response, 'status_code', 0)

            logger.info(f"Register response status: {status}")

            if status == 403:
                # Try one rebuild + retry before giving up
                can_retry = self._handle_403(response, context="register_player")
                if can_retry and self._ensure_authenticated():
                    response = self._post(url, payload, timeout=30)
                    status = getattr(response, 'status_code', 0)
                    logger.info(f"Register retry status: {status}")

                if status == 403:
                    text = getattr(response, 'text', '')
                    if _is_cloudflare_block(response):
                        return {'success': False, 'error': 'Cloudflare يحظر الاتصال - يرجى المحاولة لاحقاً'}
                    return {'success': False, 'error': 'فشل في التسجيل - خطأ 403'}

            if status == 422:
                try:
                    data = response.json()
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
                data = response.json()
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

    def get_players_for_current_agent(self, player_id=None, username=None, limit=20):
        """Get players for the current agent."""
        if not self._ensure_authenticated():
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

            response = self._post(url, payload, timeout=30)
            status = getattr(response, 'status_code', 0)

            if status == 403:
                can_retry = self._handle_403(response, context="get_players")
                if can_retry and self._ensure_authenticated():
                    response = self._post(url, payload, timeout=30)
                    status = getattr(response, 'status_code', 0)

            if status != 200:
                return {'success': False, 'error': f'HTTP {status}'}

            try:
                data = response.json()
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

    def get_player_balance_by_id(self, player_id):
        """Get player balance by ID."""
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}

        try:
            url = f"{self.API_BASE}/UserApi/getPlayerBalanceById"
            payload = {"playerId": player_id}

            response = self._post(url, payload, timeout=30)
            status = getattr(response, 'status_code', 0)

            if status == 403:
                can_retry = self._handle_403(response, context="get_balance")
                if can_retry and self._ensure_authenticated():
                    response = self._post(url, payload, timeout=30)
                    status = getattr(response, 'status_code', 0)

            if status != 200:
                return {'success': False, 'error': f'HTTP {status}'}

            try:
                data = response.json()
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

    # =============================
    # TRANSACTIONS
    # =============================
    def deposit_to_player(self, player_id, amount, comment="Bot deposit", currency="NSP"):
        """Deposit money to player account."""
        if not self._ensure_authenticated():
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
            response = self._post(url, payload, timeout=30)
            status = getattr(response, 'status_code', 0)

            if status == 403:
                can_retry = self._handle_403(response, context="deposit")
                if can_retry and self._ensure_authenticated():
                    response = self._post(url, payload, timeout=30)
                    status = getattr(response, 'status_code', 0)

            if status == 422:
                try:
                    data = response.json()
                    notifications = data.get('notification', [])
                    if notifications:
                        return {'success': False, 'error': notifications[0].get('content', 'Deposit failed')}
                except Exception:
                    pass
                return {'success': False, 'error': 'Validation failed'}

            if status != 200:
                return {'success': False, 'error': f'HTTP {status}'}

            try:
                data = response.json()
            except Exception:
                return {'success': False, 'error': 'Invalid JSON response'}

            if not data.get('status'):
                notifications = data.get('notification', [])
                if notifications:
                    return {'success': False, 'error': notifications[0].get('content', 'Deposit failed')}
                return {'success': False, 'error': 'Deposit failed'}

            result = data.get('result', {})
            new_balance = result.get('balance', 0)
            return {'success': True, 'new_balance': new_balance, 'data': data}

        except Exception as e:
            logger.error(f"Deposit error: {e}")
            return {'success': False, 'error': str(e)}

    def withdraw_from_player(self, player_id, amount, comment="Bot withdraw", currency="NSP"):
        """Withdraw money from player account."""
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}

        try:
            url = f"{self.API_BASE}/UserApi/withdrawFromPlayer"
            payload = {
                "amount": -float(amount),  # Negative for withdrawal
                "comment": comment,
                "playerId": player_id,
                "currencyCode": currency,
                "currency": currency,
                "moneyStatus": 5
            }

            logger.info(f"Withdrawing {amount} {currency} from player {player_id}")
            response = self._post(url, payload, timeout=30)
            status = getattr(response, 'status_code', 0)

            if status == 403:
                can_retry = self._handle_403(response, context="withdraw")
                if can_retry and self._ensure_authenticated():
                    response = self._post(url, payload, timeout=30)
                    status = getattr(response, 'status_code', 0)

            if status == 422:
                try:
                    data = response.json()
                    notifications = data.get('notification', [])
                    if notifications:
                        return {'success': False, 'error': notifications[0].get('content', 'Withdrawal failed')}
                except Exception:
                    pass
                return {'success': False, 'error': 'Validation failed'}

            if status != 200:
                return {'success': False, 'error': f'HTTP {status}'}

            try:
                data = response.json()
            except Exception:
                return {'success': False, 'error': 'Invalid JSON response'}

            if not data.get('status'):
                notifications = data.get('notification', [])
                if notifications:
                    return {'success': False, 'error': notifications[0].get('content', 'Withdrawal failed')}
                return {'success': False, 'error': 'Withdrawal failed'}

            result = data.get('result', {})
            new_balance = result.get('balance', 0)
            return {'success': True, 'new_balance': new_balance, 'data': data}

        except Exception as e:
            logger.error(f"Withdraw error: {e}")
            return {'success': False, 'error': str(e)}

    # =============================
    # AGENT WALLET
    # =============================
    def get_agent_wallets(self):
        """Get agent wallet information."""
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}

        try:
            url = f"{self.API_BASE}/UserApi/getAgentAllWallets"
            payload = {}

            response = self._post(url, payload, timeout=30)
            status = getattr(response, 'status_code', 0)

            if status == 403:
                can_retry = self._handle_403(response, context="get_wallets")
                if can_retry and self._ensure_authenticated():
                    response = self._post(url, payload, timeout=30)
                    status = getattr(response, 'status_code', 0)

            if status != 200:
                return {'success': False, 'error': f'HTTP {status}'}

            try:
                data = response.json()
            except Exception:
                return {'success': False, 'error': 'Invalid JSON response'}

            if not data.get('status'):
                return {'success': False, 'error': 'API request failed'}

            wallets = data.get('result', [])
            return {'success': True, 'wallets': wallets, 'data': data}

        except Exception as e:
            logger.error(f"Get agent wallets error: {e}")
            return {'success': False, 'error': str(e)}

    # =============================
    # HELPER METHODS
    # =============================
    def get_player_id_by_username(self, username):
        """Get player ID by username."""
        result = self.get_players_for_current_agent(username=username)
        if result['success']:
            return result['player'].get('playerId')
        return None

    def get_player_balance_by_username(self, username):
        """Get player balance by username."""
        player_id = self.get_player_id_by_username(username)
        if player_id:
            return self.get_player_balance_by_id(player_id)
        return {'success': False, 'error': 'Player not found'}

    def deposit_to_player_by_username(self, username, amount, comment="Bot deposit"):
        """Deposit to player by username."""
        player_id = self.get_player_id_by_username(username)
        if player_id:
            return self.deposit_to_player(player_id, amount, comment)
        return {'success': False, 'error': 'Player not found'}

    def withdraw_from_player_by_username(self, username, amount, comment="Bot withdraw"):
        """Withdraw from player by username."""
        player_id = self.get_player_id_by_username(username)
        if player_id:
            return self.withdraw_from_player(player_id, amount, comment)
        return {'success': False, 'error': 'Player not found'}


# =============================
# LEGACY COMPATIBILITY
# =============================
class iChancyAPI_Legacy(iChancyAPI):
    """Legacy compatibility wrapper."""

    def register_account(self, username, password, email, parent_id="2613607"):
        result = self.register_player(username, password, email, parent_id)
        if result['success']:
            return {'success': True, 'data': result['data']}
        return result

    def getPlayerId(self, username):
        return self.get_player_id_by_username(username)

    def getPlayerIdFast(self, username):
        return self.get_player_id_by_username(username)

    def transferMoney(self, player_id, amount, currency="NSP"):
        result = self.deposit_to_player(player_id, amount, "Bot transfer", currency)
        return result['success']

    def withdrawMoney(self, player_id, amount, currency="NSP"):
        result = self.withdraw_from_player(player_id, amount, "Bot withdrawal", currency)
        return result['success']
