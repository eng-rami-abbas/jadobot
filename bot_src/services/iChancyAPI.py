import cloudscraper
import json
import time
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class iChancyAPI:
    """
    Fixed iChancy API implementation using cloudscraper to bypass Cloudflare
    Uses proper authentication with access tokens and refresh tokens
    """
    
    BASE_URL = 'https://agents.ichancy.com'
    API_BASE = f'{BASE_URL}/global/api'
    
    def __init__(self):
        # Use cloudscraper instead of requests to bypass Cloudflare
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.agent_id = None
        
        # Setup headers
        self.scraper.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.BASE_URL,
            'Referer': self.BASE_URL + '/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Connection': 'keep-alive'
        })
        
        # Auto login on initialization
        self._ensure_authenticated()
    
    # =============================
    # 🔐 AUTHENTICATION
    # =============================
    def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        try:
            # Check if we need to login or refresh
            if not self.access_token or self._is_token_expired():
                if self.refresh_token and not self._is_refresh_token_expired():
                    logger.info("Token expired, attempting refresh...")
                    if not self._refresh_token():
                        logger.info("Refresh failed, performing new sign-in...")
                        self._sign_in()
                else:
                    logger.info("No valid tokens, performing sign-in...")
                    self._sign_in()
            
            # Verify token is set
            if not self.access_token:
                logger.error("Failed to obtain access token")
                return False
            
            # Update Authorization header
            self.scraper.headers['Authorization'] = f'Bearer {self.access_token}'
            return True
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return False
    
    def _is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_expires_at:
            return True
        return datetime.now() >= self.token_expires_at
    
    def _is_refresh_token_expired(self):
        """Check if refresh token is expired (7 days TTL)"""
        # Refresh tokens last 7 days, we'll use a conservative 6 days
        return False  # Simplified for now
    
    def _sign_in(self):
        """Sign in to get new tokens"""
        try:
            url = f"{self.API_BASE}/UserApi/signin"
            
            username = os.getenv('ICHANCY_USERNAME', '').strip()
            password = os.getenv('ICHANCY_PASSWORD', '').strip()
            
            if not username or not password:
                logger.error("❌ MISSING iChancy credentials in environment variables")
                logger.error(f"   ICHANCY_USERNAME set: {bool(os.getenv('ICHANCY_USERNAME'))}")
                logger.error(f"   ICHANCY_PASSWORD set: {bool(os.getenv('ICHANCY_PASSWORD'))}")
                logger.error("   ⚠️  SOLUTION: Configure ICHANCY_USERNAME and ICHANCY_PASSWORD in Railway/Heroku environment")
                return False
            
            payload = {
                "username": username,
                "password": password
            }
            
            logger.info("Attempting sign-in to iChancy API...")
            logger.info(f"Username: {username[:10]}..." if username else "Username: EMPTY")
            logger.info(f"Password: {'*' * 5}... (length: {len(password)})" if password else "Password: EMPTY")
            
            response = self.scraper.post(url, json=payload, timeout=30)
            
            logger.info(f"Sign-in response status: {response.status_code}")
            
            if response.status_code == 403:
                logger.error("❌ Sign-in failed: 403 Forbidden")
                logger.error("   Possible causes:")
                logger.error("   1. Invalid ICHANCY_USERNAME or ICHANCY_PASSWORD")
                logger.error("   2. Account is disabled or has no permissions")
                logger.error("   3. IP address is blocked")
                logger.error(f"   Username used: {username}")
                logger.error(f"   API URL: {url}")
                logger.error(f"   Response (first 200 chars): {response.text[:200]}")
                return False
            elif response.status_code == 401:
                logger.error("Sign-in failed: 401 Unauthorized")
                return False
            elif response.status_code != 200:
                logger.error(f"Sign-in failed with HTTP {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return False
            
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse sign-in response: {e}")
                logger.error(f"Response text: {response.text[:200]}")
                return False
            
            if not data.get('status'):
                logger.error("Sign-in API returned status=false")
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
            
            # Set token expiration (1 hour from now)
            self.token_expires_at = datetime.now() + timedelta(hours=1)
            
            # Update session headers with token
            self.scraper.headers['Authorization'] = f'Bearer {self.access_token}'
            
            logger.info("Successfully signed in to iChancy API")
            logger.debug(f"Token expires at: {self.token_expires_at}")
            return True
            
        except Exception as e:
            logger.error(f"Sign-in exception: {e}", exc_info=True)
            return False
            response = self.scraper.post(url, json=payload, timeout=30)
            
            logger.info(f"Sign in response: {response.status_code}")
            logger.debug(f"Sign in raw: {response.text}")
            
            if response.status_code == 403:
                logger.error("Sign in failed: 403 Forbidden - Invalid credentials or access denied")
                logger.error(f"Username: {payload['username']}")
                logger.error(f"Password: {'*' * len(payload['password']) if payload['password'] else 'EMPTY'}")
                logger.error(f"URL: {url}")
                logger.error(f"Headers: {dict(self.scraper.headers)}")
                return False
            elif response.status_code != 200:
                logger.error(f"Sign in failed: {response.status_code}")
                return False
            
            try:
                data = response.json()
            except:
                logger.error("Invalid JSON response from sign in")
                return False
            
            if not data.get('status') or not data.get('result'):
                logger.error("Sign in failed: Invalid response")
                return False
            
            result = data['result']
            self.access_token = result.get('accessToken')
            self.refresh_token = result.get('refreshToken')
            
            # Set token expiration (1 hour from now)
            self.token_expires_at = datetime.now() + timedelta(hours=1)
            
            # Update session headers with token
            self.scraper.headers['Authorization'] = f'Bearer {self.access_token}'
            
            logger.info("Successfully signed in to iChancy API")
            return True
            
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            return False
    
    def _refresh_token(self):
        """Refresh access token using refresh token"""
        try:
            url = f"{self.API_BASE}/UserApi/refreshToken"
            
            payload = {
                "refreshToken": self.refresh_token
            }
            
            logger.info("Refreshing iChancy API token...")
            
            response = self.scraper.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                logger.error("Token refresh failed, trying to sign in again")
                return self._sign_in()
            
            try:
                data = response.json()
            except:
                logger.error("Invalid JSON response from token refresh")
                return False
            
            if not data.get('status') or not data.get('result'):
                logger.error("Token refresh failed: Invalid response")
                return self._sign_in()
            
            result = data['result']
            self.access_token = result.get('accessToken')
            self.refresh_token = result.get('refreshToken')
            
            # Update token expiration
            self.token_expires_at = datetime.now() + timedelta(hours=1)
            
            # Update session headers
            self.scraper.headers['Authorization'] = f'Bearer {self.access_token}'
            
            logger.info("Successfully refreshed iChancy API token")
            return True
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False
    
    # =============================
    # 👤 PLAYER MANAGEMENT
    # =============================
    def register_player(self, username, password, email, parent_id=None):
        """Register a new player using the official API"""
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}
        
        try:
            url = f"{self.API_BASE}/UserApi/registerPlayer"
            
            # Use provided parent_id or default from env
            if not parent_id:
                parent_id = os.getenv('ICHANCY_PARENT_ID', '2613607')
            
            # Ensure parent_id is a string
            parent_id = str(parent_id)
            
            payload = {
                "player": {
                    "login": username,
                    "email": email,
                    "password": password,
                    "parentId": parent_id
                }
            }
            
            logger.info(f"Registering player: {username}")
            logger.info(f"Using parent_id: {parent_id}")
            logger.info(f"Registration payload: {payload}")
            logger.info(f"Registration URL: {url}")
            logger.info(f"Access token present: {bool(self.access_token)}")
            
            response = self.scraper.post(url, json=payload, timeout=30)
            
            logger.info(f"Register response status: {response.status_code}")
            logger.debug(f"Register raw response: {response.text[:500]}")
            
            if response.status_code == 422:
                # Handle validation errors
                try:
                    data = response.json()
                    logger.error(f"422 Validation error: {data}")
                    notifications = data.get('notification', [])
                    if notifications:
                        error_msg = notifications[0].get('content', 'Registration failed')
                        logger.error(f"422 Error message: {error_msg}")
                        return {'success': False, 'error': error_msg}
                    else:
                        logger.error("422 Response has no notification")
                except Exception as e:
                    logger.error(f"Error parsing 422 response: {e}")
                    logger.error(f"Raw response: {response.text}")
                return {'success': False, 'error': 'Validation error'}
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} error")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
            
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON: {e}")
                logger.error(f"Response text: {response.text}")
                return {'success': False, 'error': 'Invalid JSON response'}
            
            logger.info(f"API response status: {data.get('status')}")
            
            # Check if status is false (error occurred but HTTP 200)
            if not data.get('status'):
                notifications = data.get('notification', [])
                if notifications:
                    error_msg = notifications[0].get('content', 'Registration failed')
                    logger.error(f"API error: {error_msg}")
                    return {'success': False, 'error': error_msg}
                logger.error("API returned status=false with no error message")
                return {'success': False, 'error': 'Registration failed'}
            
            # Success case: result contains player ID (return value is 1 or similar)
            player_id = data.get('result')
            logger.info(f"Registration successful! Player ID response: {player_id}")
            
            return {'success': True, 'player_id': player_id, 'data': data}
            
        except Exception as e:
            logger.error(f"Register player exception: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def get_players_for_current_agent(self, player_id=None, username=None, limit=20):
        """Get players for the current agent"""
        if not self._ensure_authenticated():
            logger.error("Authentication failed in get_players_for_current_agent")
            return {'success': False, 'error': 'Authentication failed'}
        
        try:
            url = f"{self.API_BASE}/UserApi/getPlayersForCurrentAgent"
            
            payload = {
                "start": 0,
                "limit": limit,
                "filter": {}
            }
            
            # Add filter if provided
            if player_id:
                payload["filter"]["playerId"] = {
                    "action": "=",
                    "value": str(player_id),
                    "valueLabel": str(player_id)
                }
                logger.info(f"Searching for player by ID: {player_id}")
            elif username:
                payload["filter"]["userName"] = {
                    "action": "=",
                    "value": username,
                    "valueLabel": username
                }
                logger.info(f"Searching for player by username: {username}")
            
            logger.debug(f"Get players payload: {payload}")
            
            response = self.scraper.post(url, json=payload, timeout=30)
            
            logger.info(f"Get players response: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} from get_players")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
            
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse get_players response: {e}")
                return {'success': False, 'error': 'Invalid JSON response'}
            
            if not data.get('status'):
                logger.warning("API returned status=false in get_players")
                return {'success': False, 'error': 'API request failed'}
            
            result = data.get('result', {})
            records = result.get('records', []) if result else []
            
            logger.info(f"Found {len(records)} player records")
            
            if records and len(records) > 0:
                player_data = records[0]
                logger.info(f"Returning player: {player_data.get('username', 'unknown')}")
                return {'success': True, 'player': player_data, 'data': data}
            else:
                logger.warning(f"No player found with given criteria")
                return {'success': False, 'error': 'Player not found'}
            
        except Exception as e:
            logger.error(f"Get players exception: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def get_player_balance_by_id(self, player_id):
        """Get player balance by ID"""
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}
        
        try:
            url = f"{self.API_BASE}/UserApi/getPlayerBalanceById"
            
            payload = {
                "playerId": player_id
            }
            
            response = self.scraper.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
            
            try:
                data = response.json()
            except:
                return {'success': False, 'error': 'Invalid JSON response'}
            
            if not data.get('status'):
                return {'success': False, 'error': 'API request failed'}
            
            balances = data.get('result', [])
            
            if balances and len(balances) > 0:
                balance_info = balances[0]  # Get main currency balance
                return {'success': True, 'balance': balance_info.get('balance', 0), 'data': data}
            else:
                return {'success': True, 'balance': 0, 'data': data}
            
        except Exception as e:
            logger.error(f"Get player balance error: {e}")
            return {'success': False, 'error': str(e)}
    
    # =============================
    # 💰 TRANSACTIONS
    # =============================
    def deposit_to_player(self, player_id, amount, comment="Bot deposit", currency="NSP"):
        """Deposit money to player account"""
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
            
            response = self.scraper.post(url, json=payload, timeout=30)
            
            logger.info(f"Deposit response: {response.status_code}")
            logger.debug(f"Deposit raw: {response.text}")
            
            if response.status_code == 422:
                # Handle validation errors
                try:
                    data = response.json()
                    notifications = data.get('notification', [])
                    if notifications:
                        error_msg = notifications[0].get('content', 'Deposit failed')
                        return {'success': False, 'error': error_msg}
                except:
                    pass
                return {'success': False, 'error': 'Validation failed'}
            
            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
            
            try:
                data = response.json()
            except:
                return {'success': False, 'error': 'Invalid JSON response'}
            
            if not data.get('status'):
                notifications = data.get('notification', [])
                if notifications:
                    error_msg = notifications[0].get('content', 'Deposit failed')
                    return {'success': False, 'error': error_msg}
                return {'success': False, 'error': 'Deposit failed'}
            
            result = data.get('result', {})
            new_balance = result.get('balance', 0)
            
            return {'success': True, 'new_balance': new_balance, 'data': data}
            
        except Exception as e:
            logger.error(f"Deposit to player error: {e}")
            return {'success': False, 'error': str(e)}
    
    def withdraw_from_player(self, player_id, amount, comment="Bot withdraw", currency="NSP"):
        """Withdraw money from player account"""
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}
        
        try:
            url = f"{self.API_BASE}/UserApi/withdrawFromPlayer"
            
            payload = {
                "amount": -float(amount),  # Negative amount for withdrawal
                "comment": comment,
                "playerId": player_id,
                "currencyCode": currency,
                "currency": currency,
                "moneyStatus": 5
            }
            
            logger.info(f"Withdrawing {amount} {currency} from player {player_id}")
            
            response = self.scraper.post(url, json=payload, timeout=30)
            
            logger.info(f"Withdraw response: {response.status_code}")
            logger.debug(f"Withdraw raw: {response.text}")
            
            if response.status_code == 422:
                # Handle validation errors
                try:
                    data = response.json()
                    notifications = data.get('notification', [])
                    if notifications:
                        error_msg = notifications[0].get('content', 'Withdrawal failed')
                        return {'success': False, 'error': error_msg}
                except:
                    pass
                return {'success': False, 'error': 'Validation failed'}
            
            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
            
            try:
                data = response.json()
            except:
                return {'success': False, 'error': 'Invalid JSON response'}
            
            if not data.get('status'):
                notifications = data.get('notification', [])
                if notifications:
                    error_msg = notifications[0].get('content', 'Withdrawal failed')
                    return {'success': False, 'error': error_msg}
                return {'success': False, 'error': 'Withdrawal failed'}
            
            result = data.get('result', {})
            new_balance = result.get('balance', 0)
            
            return {'success': True, 'new_balance': new_balance, 'data': data}
            
        except Exception as e:
            logger.error(f"Withdraw from player error: {e}")
            return {'success': False, 'error': str(e)}
    
    # =============================
    # 🏪 AGENT WALLET
    # =============================
    def get_agent_wallets(self):
        """Get agent wallet information"""
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}
        
        try:
            url = f"{self.API_BASE}/UserApi/getAgentAllWallets"
            
            payload = {}
            
            response = self.scraper.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
            
            try:
                data = response.json()
            except:
                return {'success': False, 'error': 'Invalid JSON response'}
            
            if not data.get('status'):
                return {'success': False, 'error': 'API request failed'}
            
            wallets = data.get('result', [])
            
            return {'success': True, 'wallets': wallets, 'data': data}
            
        except Exception as e:
            logger.error(f"Get agent wallets error: {e}")
            return {'success': False, 'error': str(e)}
    
    # =============================
    # 🔍 HELPER METHODS
    # =============================
    def get_player_id_by_username(self, username):
        """Get player ID by username (helper method)"""
        result = self.get_players_for_current_agent(username=username)
        if result['success']:
            return result['player'].get('playerId')
        return None
    
    def get_player_balance_by_username(self, username):
        """Get player balance by username (helper method)"""
        player_id = self.get_player_id_by_username(username)
        if player_id:
            return self.get_player_balance_by_id(player_id)
        return {'success': False, 'error': 'Player not found'}
    
    def deposit_to_player_by_username(self, username, amount, comment="Bot deposit"):
        """Deposit to player by username (helper method)"""
        player_id = self.get_player_id_by_username(username)
        if player_id:
            return self.deposit_to_player(player_id, amount, comment)
        return {'success': False, 'error': 'Player not found'}
    
    def withdraw_from_player_by_username(self, username, amount, comment="Bot withdraw"):
        """Withdraw from player by username (helper method)"""
        player_id = self.get_player_id_by_username(username)
        if player_id:
            return self.withdraw_from_player(player_id, amount, comment)
        return {'success': False, 'error': 'Player not found'}


# =============================
# 🔧 LEGACY COMPATIBILITY
# =============================
# For backward compatibility with existing code
class iChancyAPI_Legacy(iChancyAPI):
    """Legacy compatibility wrapper"""
    
    def register_account(self, username, password, email, parent_id="2613607"):
        """Legacy method name"""
        result = self.register_player(username, password, email, parent_id)
        if result['success']:
            return {'success': True, 'data': result['data']}
        else:
            return result
    
    def getPlayerId(self, username):
        """Legacy method name"""
        return self.get_player_id_by_username(username)
    
    def getPlayerIdFast(self, username):
        """Legacy method name"""
        return self.get_player_id_by_username(username)
    
    def transferMoney(self, player_id, amount, currency="NSP"):
        """Legacy method name"""
        result = self.deposit_to_player(player_id, amount, "Bot transfer", currency)
        return result['success']
    
    def withdrawMoney(self, player_id, amount, currency="NSP"):
        """Legacy method name"""
        result = self.withdraw_from_player(player_id, amount, "Bot withdrawal", currency)
        return result['success']
