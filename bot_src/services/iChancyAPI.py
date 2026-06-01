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
