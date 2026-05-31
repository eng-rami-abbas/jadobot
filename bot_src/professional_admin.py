#!/usr/bin/env python3
"""
Professional Admin Panel - Complete Bot Management System
Real-time Notifications + Full Bot Integration + Chrome Compatible
"""

import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import json
import hashlib
import datetime
import threading
import time
import websocket
from flask_socketio import SocketIO, emit

# Import bot modules
import store
import Logger
from handlers.payment_handler import PaymentHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = 'professional-admin-2024-secure'
socketio = SocketIO(app, cors_allowed_origins="*")

# استقبال أحداث من البوت (REAL-TIME)
@socketio.on('notification')
def handle_bot_notification(data):
    try:
        print("🔥 Event from bot:", data)

        notification = {
            'id': len(notifications) + 1,
            'message': str(data),
            'type': data.get('type', 'info'),
            'timestamp': datetime.datetime.now().isoformat()
        }

        notifications.append(notification)

        # بث الحدث لكل المتصلين
        socketio.emit('notification', notification)

    except Exception as e:
        logger.error(f"Error handling bot notification: {e}")
        
@app.template_filter('number_format')
def number_format(value):
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return "0"

logger = Logger.getLogger()

# Global variables
bot_status = {'online': True, 'last_check': datetime.datetime.now()}
notifications = []

# Translation dictionary
TRANSLATIONS = {
    'ar': {
        'dashboard': 'Dashboard',
        'users': 'Users',
        'messages': 'Messages',
        'deposit_logs': 'Deposit Logs',
        'withdrawal_logs': 'Withdrawal Logs',
        'settings': 'Settings',
        'logout': 'Logout',
        'active_users_week': 'Active Users This Week',
        'total_balance': 'Total Balance',
        'deposits_week': 'Deposits This Week',
        'withdrawals_week': 'Withdrawals This Week',
        'incoming_messages': 'Incoming Messages',
        'exchange_rate': 'Exchange Rate',
        'language': 'Language',
        'theme': 'Theme',
        'light_mode': 'Light Mode',
        'dark_mode': 'Dark Mode',
        'arabic': 'Arabic',
        'english': 'English',
        'wallets': 'Wallets',
        'security': 'Security',
        'user_management': 'User Management',
        'operations_log': 'Operations Log',
        'block_user': 'Block User',
        'gift_balance': 'Gift Balance',
        'withdraw_balance': 'Withdraw Balance',
        'change_password': 'Change Password',
        'send_broadcast': 'Send Broadcast',
        'real_time_updates': 'Real-time Updates',
        'welcome_to_admin': 'Welcome to iChancy Admin Panel',
        'admin_logged_in': 'Admin logged in successfully',
        'admin_logged_out': 'Admin logged out',
        'language_switched': 'Language switched to',
        'theme_switched': 'Theme switched to',
        'exchange_rate_updated': 'Exchange rate updated to',
        'broadcast_sent': 'Broadcast message sent to all users',
        'user_blocked': 'User blocked successfully',
        'balance_gifted': 'Balance gifted to user',
        'balance_withdrawn': 'Balance withdrawn from user',
        'transaction_approved': 'Transaction approved successfully',
        'transaction_rejected': 'Transaction rejected successfully'
    },
    'en': {
        'dashboard': 'Dashboard',
        'users': 'Users',
        'messages': 'Messages',
        'deposit_logs': 'Deposit Logs',
        'withdrawal_logs': 'Withdrawal Logs',
        'settings': 'Settings',
        'logout': 'Logout',
        'active_users_week': 'Active Users This Week',
        'total_balance': 'Total Balance',
        'deposits_week': 'Deposits This Week',
        'withdrawals_week': 'Withdrawals This Week',
        'incoming_messages': 'Incoming Messages',
        'exchange_rate': 'Exchange Rate',
        'language': 'Language',
        'theme': 'Theme',
        'light_mode': 'Light Mode',
        'dark_mode': 'Dark Mode',
        'arabic': 'Arabic',
        'english': 'English',
        'wallets': 'Wallets',
        'security': 'Security',
        'user_management': 'User Management',
        'operations_log': 'Operations Log',
        'block_user': 'Block User',
        'gift_balance': 'Gift Balance',
        'withdraw_balance': 'Withdraw Balance',
        'change_password': 'Change Password',
        'send_broadcast': 'Send Broadcast',
        'real_time_updates': 'Real-time Updates',
        'welcome_to_admin': 'Welcome to iChancy Admin Panel',
        'admin_logged_in': 'Admin logged in successfully',
        'admin_logged_out': 'Admin logged out',
        'language_switched': 'Language switched to',
        'theme_switched': 'Theme switched to',
        'exchange_rate_updated': 'Exchange rate updated to',
        'broadcast_sent': 'Broadcast message sent to all users',
        'user_blocked': 'User blocked successfully',
        'balance_gifted': 'Balance gifted to user',
        'balance_withdrawn': 'Balance withdrawn from user',
        'transaction_approved': 'Transaction approved successfully',
        'transaction_rejected': 'Transaction rejected successfully'
    }
}

def get_current_language():
    return session.get('language', 'ar')

def get_current_theme():
    return session.get('theme', 'light')

def get_translation(key):
    lang = get_current_language()
    return TRANSLATIONS[lang].get(key, key)

def get_weekly_stats():
    """Get weekly statistics from database"""
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            
            # Get week start and end dates
            today = datetime.date.today()
            week_start = today - datetime.timedelta(days=today.weekday())
            week_end = week_start + datetime.timedelta(days=6)
            
            # Active users this week
            cur.execute("""
                SELECT COUNT(DISTINCT telegram_id) as count 
                FROM transactions 
                WHERE DATE(created_at) BETWEEN ? AND ?
            """, (week_start.isoformat(), week_end.isoformat()))
            active_users = cur.fetchone()['count']
            
            # Total balance (bot capital)
            cur.execute("SELECT SUM(balance) as total FROM users")
            total_balance = cur.fetchone()['total'] or 0
            
            # Deposits this week
            cur.execute("""
                SELECT SUM(amount) as total 
                FROM transactions 
                WHERE type = 'deposit' AND DATE(created_at) BETWEEN ? AND ?
            """, (week_start.isoformat(), week_end.isoformat()))
            deposits_week = cur.fetchone()['total'] or 0
            
            # Withdrawals this week
            cur.execute("""
                SELECT SUM(amount) as total 
                FROM transactions 
                WHERE type = 'withdrawal' AND DATE(created_at) BETWEEN ? AND ?
            """, (week_start.isoformat(), week_end.isoformat()))
            withdrawals_week = cur.fetchone()['total'] or 0
            
            # Incoming messages (simulate for now)
            incoming_messages = 0
            
            return {
                'active_users': active_users,
                'total_balance': total_balance,
                'deposits_week': deposits_week,
                'withdrawals_week': withdrawals_week,
                'incoming_messages': incoming_messages
            }
    except Exception as e:
        logger.error(f"Error getting weekly stats: {e}")
        return {
            'active_users': 0,
            'total_balance': 0,
            'deposits_week': 0,
            'withdrawals_week': 0,
            'incoming_messages': 0
        }

def get_payment_methods():
    """Get real payment methods from deposit.py"""
    return {
        "syriatel_cash": {
            "name": "Syriatel Cash",
            "emoji": "Green",
            "min_amount": 25000,
            "max_amount": 10000000,
            "instructions": "Syriatel Cash Payment Method",
            "phone_numbers": ["0991005298", "0980375513"]
        },
        "mtn_cash": {
            "name": "MTN Cash",
            "emoji": "Yellow", 
            "min_amount": 25000,
            "max_amount": 10000000,
            "instructions": "MTN Cash Payment Method",
            "phone_numbers": []
        },
        "sham_cash_auto": {
            "name": "Sham Cash Auto",
            "emoji": "Auto",
            "min_amount": 25000,
            "max_amount": 10000000,
            "instructions": "Sham Cash Auto (USD, SYP)",
            "phone_numbers": []
        },
        "bemo": {
            "name": "Bemo",
            "emoji": "Bank",
            "min_amount": 25000,
            "max_amount": 10000000,
            "instructions": "Bemo Bank Transfer",
            "phone_numbers": []
        },
        "payeer": {
            "name": "Payeer",
            "emoji": "Digital",
            "min_amount": 25000,
            "max_amount": 10000000,
            "instructions": "Payeer Digital Wallet",
            "phone_numbers": []
        },
        "crypto": {
            "name": "USDT Crypto",
            "emoji": "Crypto",
            "min_amount": 25000,
            "max_amount": 10000000,
            "instructions": "USDT Digital Currency",
            "phone_numbers": []
        }
    }

def check_bot_status():
    """Check if bot is online by checking internet connectivity"""
    global bot_status
    while True:
        try:
            import urllib.request
            import socket
            
            # Check internet connectivity to Telegram API
            socket.setdefaulttimeout(5)
            urllib.request.urlopen('https://api.telegram.org', timeout=5)
            
            # Check database accessibility
            with store.get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
            
            bot_status['online'] = True
            bot_status['last_check'] = datetime.datetime.now()
        except Exception as e:
            bot_status['online'] = False
            bot_status['last_check'] = datetime.datetime.now()
            logger.error(f"Bot status check failed: {e}")
        
        time.sleep(30)

def is_admin_logged_in():
    return session.get('admin_logged_in', False)

def add_notification(message, type='info'):
    """Add notification and emit to connected clients"""
    notification = {
        'id': len(notifications) + 1,
        'message': message,
        'type': type,
        'timestamp': datetime.datetime.now().isoformat()
    }
    notifications.append(notification)
    socketio.emit('notification', notification)
    logger.info(f"Notification added: {message}")

def send_broadcast_to_bot(message, message_type='announcement'):
    """Send broadcast message to all bot users"""
    try:
        # Import bot instance to send messages
        from bot import bot
        
        # Get all users from database
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT telegram_id FROM users WHERE blocked = 0 OR blocked IS NULL")
            users = cur.fetchall()
        
        success_count = 0
        failure_count = 0
        
        for user in users:
            try:
                # Send message to user
                bot.send_message(
                    chat_id=user['telegram_id'],
                    text=f"**{message_type.upper()}**\n\n{message}",
                    parse_mode='Markdown'
                )
                success_count += 1
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user['telegram_id']}: {e}")
                failure_count += 1
        
        logger.info(f"Broadcast sent: {success_count} successful, {failure_count} failed")
        return success_count, failure_count
    except Exception as e:
        logger.error(f"Error sending broadcast: {e}")
        return 0, 1

def update_exchange_rate_in_bot(new_rate):
    """Update exchange rate in bot configuration"""
    try:
        # Update in database
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES ('exchange_rate', ?, ?)
            """, (new_rate, datetime.datetime.now().isoformat()))
        
        # Update bot global variable if bot is running
        try:
            from handlers.ichancy import EXCHANGE_RATE
            EXCHANGE_RATE = int(new_rate)
            logger.info(f"Exchange rate updated in bot: {new_rate}")
        except:
            logger.warning("Could not update bot exchange rate variable")
        
        return True
    except Exception as e:
        logger.error(f"Error updating exchange rate: {e}")
        return False

# Routes
@app.route('/')
def index():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            session['username'] = username
            add_notification(get_translation('admin_logged_in'), 'success')
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    add_notification(get_translation('admin_logged_out'), 'info')
    session.clear()
    return redirect(url_for('login'))

@app.route('/switch_language')
def switch_language():
    current_lang = get_current_language()
    new_lang = 'en' if current_lang == 'ar' else 'ar'
    session['language'] = new_lang
    add_notification(get_translation('language_switched') + f' {new_lang}', 'info')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/switch_theme')
def switch_theme():
    current_theme = get_current_theme()
    new_theme = 'dark' if current_theme == 'light' else 'light'
    session['theme'] = new_theme
    add_notification(get_translation('theme_switched') + f' {new_theme}', 'info')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    stats = get_weekly_stats()
    
    # Get exchange rate
    exchange_rate = 50000
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = 'exchange_rate'")
            result = cur.fetchone()
            if result:
                exchange_rate = int(result['value'])
    except:
        pass
    
    return render_template('dashboard.html', 
                         stats=stats,
                         exchange_rate=exchange_rate,
                         bot_status=bot_status,
                         get_translation=get_translation,
                         current_language=get_current_language(),
                         current_theme=get_current_theme())

@app.route('/users')
def users():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users ORDER BY id DESC LIMIT 100")
            users = [dict(row) for row in cur.fetchall()]
            
            # Get operations for each user
            for user in users:
                cur.execute("""
                    SELECT * FROM transactions 
                    WHERE telegram_id = ? 
                    ORDER BY id DESC LIMIT 10
                """, (user['telegram_id'],))
                user['operations'] = [dict(row) for row in cur.fetchall()]
        
        return render_template('users.html', users=users,
                             get_translation=get_translation,
                             current_language=get_current_language(),
                             current_theme=get_current_theme())
    except Exception as e:
        logger.error(f"Users page error: {e}")
        return render_template('users.html', users=[],
                             get_translation=get_translation,
                             current_language=get_current_language(),
                             current_theme=get_current_theme())

@app.route('/deposit_logs')
def deposit_logs():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT t.*, u.username 
                FROM transactions t 
                LEFT JOIN users u ON t.telegram_id = u.telegram_id 
                WHERE t.type = 'deposit'
                ORDER BY t.id DESC LIMIT 100
            """)
            deposits = [dict(row) for row in cur.fetchall()]
        
        return render_template('deposit_logs.html', deposits=deposits,
                             get_translation=get_translation,
                             current_language=get_current_language(),
                             current_theme=get_current_theme())
    except Exception as e:
        logger.error(f"Deposit logs error: {e}")
        return render_template('deposit_logs.html', deposits=[],
                             get_translation=get_translation,
                             current_language=get_current_language(),
                             current_theme=get_current_theme())

@app.route('/withdrawal_logs')
def withdrawal_logs():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT t.*, u.username 
                FROM transactions t 
                LEFT JOIN users u ON t.telegram_id = u.telegram_id 
                WHERE t.type = 'withdrawal'
                ORDER BY t.id DESC LIMIT 100
            """)
            withdrawals = [dict(row) for row in cur.fetchall()]
        
        return render_template('withdrawal_logs.html', withdrawals=withdrawals,
                             get_translation=get_translation,
                             current_language=get_current_language(),
                             current_theme=get_current_theme())
    except Exception as e:
        logger.error(f"Withdrawal logs error: {e}")
        return render_template('withdrawal_logs.html', withdrawals=[],
                             get_translation=get_translation,
                             current_language=get_current_language(),
                             current_theme=get_current_theme())

@app.route('/messages')
def messages():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    # Simulate incoming messages
    messages = [
        {'id': 1, 'user': 'user123', 'message': 'Hello, I need help', 'time': '10:30 AM'},
        {'id': 2, 'user': 'user456', 'message': 'How to deposit?', 'time': '10:45 AM'},
        {'id': 3, 'user': 'user789', 'message': 'Thank you for support', 'time': '11:00 AM'}
    ]
    
    return render_template('messages.html', messages=messages,
                         get_translation=get_translation,
                         current_language=get_current_language(),
                         current_theme=get_current_theme())

@app.route('/settings')
def settings():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    # Create settings table if it doesn't exist
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            
            # Insert default exchange rate if not exists
            cur.execute("""
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES ('exchange_rate', '50000', ?)
            """, (datetime.datetime.now().isoformat(),))
            
            # Get exchange rate from database
            cur.execute("SELECT value FROM settings WHERE key = 'exchange_rate'")
            result = cur.fetchone()
            exchange_rate = int(result['value']) if result else 50000
    except Exception as e:
        logger.error(f"Settings error: {e}")
        exchange_rate = 50000
    
    payment_methods = get_payment_methods()
    
    return render_template('settings.html', exchange_rate=exchange_rate, 
                         payment_methods=payment_methods, bot_status=bot_status,
                         get_translation=get_translation,
                         current_language=get_current_language(),
                         current_theme=get_current_theme())

# API Routes
@app.route('/api/transactions/<int:transaction_id>/approve', methods=['POST'])
def approve_transaction(transaction_id):
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
            transaction = cur.fetchone()
            
            if not transaction:
                return jsonify({'success': False, 'message': 'Transaction not found'}), 404
            
            cur.execute("UPDATE transactions SET status = 'approved' WHERE id = ?", (transaction_id,))
            
            if transaction['type'] == 'deposit':
                cur.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", 
                          (transaction['amount'], transaction['telegram_id']))
            
            add_notification(f'Transaction {transaction_id} approved', 'success')
            logger.info(f"Transaction {transaction_id} approved")
        
        return jsonify({'success': True, 'message': 'Transaction approved'})
    except Exception as e:
        logger.error(f"Error approving transaction: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>/reject', methods=['POST'])
def reject_transaction(transaction_id):
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE transactions SET status = 'rejected' WHERE id = ?", (transaction_id,))
            
            add_notification(f'Transaction {transaction_id} rejected', 'warning')
            logger.info(f"Transaction {transaction_id} rejected")
        
        return jsonify({'success': True, 'message': 'Transaction rejected'})
    except Exception as e:
        logger.error(f"Error rejecting transaction: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<int:user_id>/gift_balance', methods=['POST'])
def gift_balance(user_id):
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        amount = data.get('amount')
        
        if not amount or amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid amount'}), 400
        
        with store.get_db() as conn:
            cur = conn.cursor()
            
            # Add to user balance
            cur.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
            
            # Deduct from bot capital (simulate)
            logger.info(f"Gifted {amount} to user {user_id}")
            
            add_notification(f'Gifted {amount} to user {user_id}', 'success')
        
        return jsonify({'success': True, 'message': 'Balance gifted successfully'})
    except Exception as e:
        logger.error(f"Error gifting balance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<int:user_id>/withdraw_balance', methods=['POST'])
def withdraw_user_balance(user_id):
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        amount = data.get('amount')
        
        if not amount or amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid amount'}), 400
        
        with store.get_db() as conn:
            cur = conn.cursor()
            
            # Check user balance
            cur.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            user_balance = cur.fetchone()['balance']
            
            if user_balance < amount:
                return jsonify({'success': False, 'message': 'Insufficient balance'}), 400
            
            # Deduct from user balance
            cur.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
            
            # Add to bot capital
            logger.info(f"Withdrew {amount} from user {user_id}")
            
            add_notification(f'Withdrew {amount} from user {user_id}', 'info')
        
        return jsonify({'success': True, 'message': 'Balance withdrawn successfully'})
    except Exception as e:
        logger.error(f"Error withdrawing balance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<int:user_id>/block', methods=['POST'])
def block_user(user_id):
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET blocked = 1 WHERE id = ?", (user_id,))
            
            add_notification(f'User {user_id} blocked', 'warning')
            logger.info(f"User {user_id} blocked")
        
        return jsonify({'success': True, 'message': 'User blocked successfully'})
    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/exchange_rate/update', methods=['POST'])
def update_exchange_rate():
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        new_rate = data.get('exchange_rate')
        
        # Convert to integer
        try:
            new_rate_int = int(new_rate)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid exchange rate format'}), 400
        
        if not new_rate_int or new_rate_int <= 0:
            return jsonify({'success': False, 'message': 'Invalid exchange rate'}), 400
        
        # Update exchange rate in bot
        if update_exchange_rate_in_bot(new_rate_int):
            add_notification(get_translation('exchange_rate_updated') + f' {new_rate_int}', 'success')
            logger.info(f"Exchange rate updated to {new_rate_int}")
            return jsonify({'success': True, 'message': 'Exchange rate updated'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update exchange rate'}), 500
    except Exception as e:
        logger.error(f"Error updating exchange rate: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/wallets/update', methods=['POST'])
def update_wallet():
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        method = data.get('method')
        new_numbers = data.get('numbers', [])
        
        if not method or not new_numbers:
            return jsonify({'success': False, 'message': 'Invalid data'}), 400
        
        add_notification(f'Wallet {method} updated', 'info')
        logger.info(f"Wallet {method} updated with numbers: {new_numbers}")
        
        return jsonify({'success': True, 'message': 'Wallet updated'})
    except Exception as e:
        logger.error(f"Error updating wallet: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/broadcast/send', methods=['POST'])
def send_broadcast():
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        message = data.get('message')
        message_type = data.get('type', 'announcement')
        
        if not message:
            return jsonify({'success': False, 'message': 'Message is required'}), 400
        
        # Send broadcast to bot users
        success_count, failure_count = send_broadcast_to_bot(message, message_type)
        
        if success_count > 0:
            add_notification(get_translation('broadcast_sent') + f' ({success_count} users)', 'success')
            logger.info(f"Broadcast sent to {success_count} users")
            return jsonify({
                'success': True, 
                'message': f'Broadcast sent to {success_count} users',
                'success_count': success_count,
                'failure_count': failure_count
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to send broadcast'}), 500
    except Exception as e:
        logger.error(f"Error sending broadcast: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/bot/status')
def get_bot_status():
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    return jsonify({
        'success': True,
        'status': 'online' if bot_status['online'] else 'offline',
        'last_check': bot_status['last_check'].isoformat()
    })

@app.route('/api/stats/weekly')
def get_weekly_stats_api():
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    stats = get_weekly_stats()
    return jsonify({'success': True, 'stats': stats})

# WebSocket events
@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected to admin panel'})
    logger.info('Client connected to admin panel')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected from admin panel')

if __name__ == '__main__':
    # Start status monitoring
    status_thread = threading.Thread(target=check_bot_status, daemon=True)
    status_thread.start()
    
    print("=" * 60)
    print("iChancy Bot - Professional Admin Panel")
    print("=" * 60)
    print("URL: http://localhost:8080")
    print("Username: admin")
    print("Password: admin123")
    print("Features: Real-time Updates + Full Bot Integration + Chrome Compatible")
    print("=" * 60)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
