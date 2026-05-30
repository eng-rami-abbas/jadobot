"""
iChancy Agent API Client
========================
Connects to agents.ichancy.com API with Cloudflare bypass.
Uses multiple strategies: cloudscraper -> requests+headers -> curl fallback.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try cloudscraper first, fall back to requests
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False


class iChancyAPI:
    """
    iChancy Agent API client with Cloudflare bypass.
    Tries cloudscraper first, then falls back to requests with browser-like headers.
    """

    BASE_URL = 'https://agents.ichancy.com'
    API_BASE = f'{BASE_URL}/global/api'

    # Singleton-like shared session to avoid re-authenticating on every call
    _shared_instance = None
    _last_auth_time = None
    _auth_ttl = timedelta(minutes=30)

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

        # Setup session with best available strategy
        self._init_session()

        # Auto login
        self._ensure_authenticated()

    def _init_session(self):
        """Initialize HTTP session with best available strategy."""
        # Strategy 1: curl_cffi (best Cloudflare bypass)
        if HAS_CURL_CFFI:
            try:
                self.session = curl_requests.Session(impersonate="chrome120")
                self._session_type = "curl_cffi"
                logger.info("Using curl_cffi session (best Cloudflare bypass)")
                return
            except Exception as e:
                logger.warning(f"curl_cffi init failed: {e}")

        # Strategy 2: cloudscraper
        if HAS_CLOUDSCRAPER:
            try:
                self.session = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'mobile': False
                    }
                )
                self._session_type = "cloudscraper"
                logger.info("Using cloudscraper session")
                return
            except Exception as e:
                logger.warning(f"cloudscraper init failed: {e}")

        # Strategy 3: plain requests with browser headers
        if HAS_REQUESTS:
            self.session = requests.Session()
            self._session_type = "requests"
            logger.info("Using plain requests session (no Cloudflare bypass)")
            return

        raise RuntimeError("No HTTP library available (need requests, cloudscraper, or curl_cffi)")

    def _setup_headers(self):
        """Configure session headers to mimic a real browser."""
        headers = {
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

        if hasattr(self.session, 'headers'):
            self.session.headers.update(headers)

    def _post(self, url, payload, timeout=30):
        """Make a POST request with the current session."""
        self._setup_headers()

        # Add auth token if available
        if self.access_token and hasattr(self.session, 'headers'):
            self.session.headers['Authorization'] = f'Bearer {self.access_token}'

        logger.debug(f"POST {url} (session type: {self._session_type})")

        if self._session_type == "curl_cffi":
            return self.session.post(url, json=payload, timeout=timeout)
        else:
            return self.session.post(url, json=payload, timeout=timeout)

    def _get(self, url, timeout=30):
        """Make a GET request with the current session."""
        self._setup_headers()

        if self.access_token and hasattr(self.session, 'headers'):
            self.session.headers['Authorization'] = f'Bearer {self.access_token}'

        if self._session_type == "curl_cffi":
            return self.session.get(url, timeout=timeout)
        else:
            return self.session.get(url, timeout=timeout)

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
                if hasattr(self.session, 'headers'):
                    self.session.headers['Authorization'] = f'Bearer {self.access_token}'
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
        """Sign in to iChancy API with retry logic."""
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

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Sign-in attempt {attempt + 1}/{max_retries}...")

                response = self._post(url, payload, timeout=45)
                status = getattr(response, 'status_code', 0)

                logger.info(f"Sign-in response status: {status}")

                if status == 403:
                    # Check if it's a Cloudflare challenge (HTML response)
                    text = getattr(response, 'text', '')
                    if '<!DOCTYPE' in text or '<html' in text.lower():
                        logger.warning(f"Cloudflare challenge detected (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            time.sleep(3 * (attempt + 1))  # Exponential backoff
                            continue
                    else:
                        logger.error("403 Forbidden - not Cloudflare, possible auth issue")
                    if attempt == max_retries - 1:
                        logger.error("All sign-in attempts blocked by Cloudflare")
                        return False
                    continue

                elif status == 401:
                    logger.error("Sign-in failed: 401 Unauthorized - check credentials")
                    return False

                elif status != 200:
                    logger.error(f"Sign-in failed with HTTP {status}")
                    resp_text = getattr(response, 'text', '')[:500]
                    logger.error(f"Response: {resp_text}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return False

                # Parse JSON response
                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"Failed to parse sign-in response: {e}")
                    text = getattr(response, 'text', '')[:200]
                    logger.error(f"Response text: {text}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
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

                if hasattr(self.session, 'headers'):
                    self.session.headers['Authorization'] = f'Bearer {self.access_token}'

                logger.info("Successfully signed in to iChancy API")
                iChancyAPI._last_auth_time = datetime.now()
                return True

            except Exception as e:
                logger.error(f"Sign-in exception (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
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

            if getattr(response, 'status_code', 0) != 200:
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

            if hasattr(self.session, 'headers'):
                self.session.headers['Authorization'] = f'Bearer {self.access_token}'

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
                text = getattr(response, 'text', '')
                if '<!DOCTYPE' in text:
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
