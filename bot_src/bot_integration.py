"""
Bot Integration Module - Connects bot events to admin panel
"""
import asyncio
import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import store
import Logger

logger = Logger.getLogger()

# عنوان لوحة التحكم
ADMIN_PANEL_URL = "http://localhost:8080/api/events"

class BotIntegration:
    def __init__(self):
        self.admin_websocket = None

    def send_event(self, event_type, data):
        """Send event to admin panel via API"""
        try:
            response = requests.post(
                ADMIN_PANEL_URL,
                json={
                    "type": event_type,
                    "data": data
                },
                timeout=5
            )
            logger.info(f"Event sent: {event_type} | Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send event: {e}")

    def notify_new_user(self, user_data):
        try:
            self.send_event('user_registered', {
                'username': user_data.get('username', 'N/A'),
                'telegram_id': user_data.get('telegram_id'),
                'timestamp': user_data.get('created_at')
            })
        except Exception as e:
            logger.error(f"Failed to notify admin about new user: {e}")

    def notify_new_transaction(self, transaction_data):
        try:
            self.send_event('transaction_created', {
                'transaction_id': transaction_data.get('id'),
                'user_id': transaction_data.get('telegram_id'),
                'username': transaction_data.get('username'),
                'type': transaction_data.get('type'),
                'amount': transaction_data.get('amount'),
                'method': transaction_data.get('method'),
                'timestamp': transaction_data.get('created_at')
            })
        except Exception as e:
            logger.error(f"Failed to notify admin about new transaction: {e}")

    def notify_transaction_approved(self, transaction_id, user_id):
        try:
            self.send_event('transaction_approved', {
                'transaction_id': transaction_id,
                'user_id': user_id
            })
        except Exception as e:
            logger.error(f"Failed to notify admin about approved transaction: {e}")

    def notify_transaction_rejected(self, transaction_id, user_id):
        try:
            self.send_event('transaction_rejected', {
                'transaction_id': transaction_id,
                'user_id': user_id
            })
        except Exception as e:
            logger.error(f"Failed to notify admin about rejected transaction: {e}")

    def notify_user_balance_updated(self, user_id, old_balance, new_balance):
        try:
            self.send_event('user_balance_updated', {
                'user_id': user_id,
                'old_balance': old_balance,
                'new_balance': new_balance
            })
        except Exception as e:
            logger.error(f"Failed to notify admin about balance update: {e}")

    def notify_bot_error(self, error_message, context=None):
        try:
            self.send_event('bot_error', {
                'error_message': error_message,
                'context': context,
                'timestamp': store.get_damascus_time().isoformat() if hasattr(store, 'get_damascus_time') else None
            })
        except Exception as e:
            logger.error(f"Failed to notify admin about bot error: {e}")

    def notify_bot_status_change(self, status, message=None):
        try:
            self.send_event('bot_status_change', {
                'status': status,
                'message': message,
                'timestamp': store.get_damascus_time().isoformat() if hasattr(store, 'get_damascus_time') else None
            })
        except Exception as e:
            logger.error(f"Failed to notify admin about status change: {e}")

    def notify_wallet_update(self, wallet_data):
        try:
            self.send_event('wallet_updated', {
                'wallet_number': wallet_data.get('number'),
                'action': wallet_data.get('action'),
                'timestamp': wallet_data.get('timestamp')
            })
        except Exception as e:
            logger.error(f"Failed to notify admin about wallet update: {e}")

    def get_admin_stats(self):
        try:
            import datetime
            with store.get_db() as conn:
                cur = conn.cursor()

                cur.execute("SELECT COUNT(*) as count FROM users")
                total_users = cur.fetchone()['count']

                today = datetime.date.today().isoformat()
                cur.execute("SELECT COUNT(*) as count FROM users WHERE DATE(created_at) = ?", (today,))
                new_users_today = cur.fetchone()['count']

                cur.execute("SELECT COUNT(*) as count FROM transactions WHERE status = 'pending'")
                pending_transactions = cur.fetchone()['count']

                cur.execute("SELECT SUM(balance) as total FROM users")
                total_balance = cur.fetchone()['total'] or 0

                return {
                    'total_users': total_users,
                    'new_users_today': new_users_today,
                    'pending_transactions': pending_transactions,
                    'total_balance': total_balance
                }
        except Exception as e:
            logger.error(f"Failed to get admin stats: {e}")
            return None


# Global instance
bot_integration = BotIntegration()


def on_user_registered(user_data):
    bot_integration.notify_new_user(user_data)


def on_transaction_created(transaction_data):
    bot_integration.notify_new_transaction(transaction_data)


def on_transaction_approved(transaction_id, user_id):
    bot_integration.notify_transaction_approved(transaction_id, user_id)


def on_transaction_rejected(transaction_id, user_id):
    bot_integration.notify_transaction_rejected(transaction_id, user_id)


def on_user_balance_updated(user_id, old_balance, new_balance):
    bot_integration.notify_user_balance_updated(user_id, old_balance, new_balance)


def on_bot_error(error_message, context=None):
    bot_integration.notify_bot_error(error_message, context)


def on_bot_status_change(status, message=None):
    bot_integration.notify_bot_status_change(status, message)


def on_wallet_update(wallet_data):
    bot_integration.notify_wallet_update(wallet_data)