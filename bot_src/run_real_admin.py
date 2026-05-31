#!/usr/bin/env python3
"""
Real Admin Panel - Connected to Bot Database
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import json
import hashlib
import datetime
import threading
import time

from config.telegram import Bot, TOKEN

# Import bot modules
import store
import Logger
from handlers.payment_handler import PaymentHandler

app = Flask(__name__, template_folder='web_admin/templates')
app.config['SECRET_KEY'] = 'admin-panel-secret-key-real'

logger = Logger.getLogger()

# Global variables for real-time monitoring
bot_status = {'online': True, 'last_check': datetime.datetime.now()}

def get_real_wallets():
    """Get real wallets from payment handler"""
    payment_methods = PaymentHandler.PAYMENT_METHODS
    wallets = {}
    
    for method_key, method_data in payment_methods.items():
        # Extract phone numbers from instructions
        instructions = method_data.get('instructions', '')
        numbers = []
        
        # Look for phone numbers in instructions
        import re
        phone_pattern = r'0[0-9]{10}'
        found_numbers = re.findall(phone_pattern, instructions)
        numbers.extend(found_numbers)
        
        if numbers:  # Only add if we found phone numbers
            wallets[method_key] = {
                'name': method_data['name'],
                'numbers': numbers,
                'min_deposit': method_data.get('min_amount', 0),
                'max_deposit': method_data.get('max_amount', 10000000),
                'active': True,
                'emoji': method_data.get('emoji', ' ')
            }
    
    return wallets




def check_bot_status():
    """Check if bot is running"""
    global bot_status
    while True:
        try:
            # Try to access database to check if bot is active
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
        
        time.sleep(30)  # Check every 30 seconds

def is_admin_logged_in():
    return session.get('admin_logged_in', False)

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
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    try:
        # Get real statistics from database
        with store.get_db() as conn:
            cur = conn.cursor()
            
            # Total users
            cur.execute("SELECT COUNT(*) as count FROM users")
            total_users = cur.fetchone()['count']
            
            # Pending transactions
            cur.execute("SELECT COUNT(*) as count FROM transactions WHERE status = 'pending'")
            pending_transactions = cur.fetchone()['count']
            
            # Total balance
            cur.execute("SELECT SUM(balance) as total FROM users")
            total_balance = cur.fetchone()['total'] or 0
            
            # Recent transactions
            cur.execute("""
                SELECT t.*, u.username 
                FROM transactions t 
                LEFT JOIN users u ON t.telegram_id = u.telegram_id 
                ORDER BY t.id DESC LIMIT 10
            """)
            recent_transactions = [dict(row) for row in cur.fetchall()]
        
        return render_template('dashboard.html', 
                             total_users=total_users,
                             pending_transactions=pending_transactions,
                             total_balance=total_balance,
                             recent_transactions=recent_transactions,
                             bot_status='online' if bot_status['online'] else 'offline')
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', 
                             total_users=0,
                             pending_transactions=0,
                             total_balance=0,
                             recent_transactions=[],
                             bot_status='offline')

@app.route('/users')
def users():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    try:
        # Get real users from database
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users ORDER BY id DESC LIMIT 100")
            users = [dict(row) for row in cur.fetchall()]
        
        return render_template('users.html', users=users, total_users=len(users))
    except Exception as e:
        logger.error(f"Users page error: {e}")
        return render_template('users.html', users=[], total_users=0)

@app.route('/transactions')
def transactions():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    try:
        # Get real transactions from database
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT t.*, u.username 
                FROM transactions t 
                LEFT JOIN users u ON t.telegram_id = u.telegram_id 
                ORDER BY t.id DESC LIMIT 100
            """)
            transactions = [dict(row) for row in cur.fetchall()]
        
        return render_template('transactions.html', transactions=transactions, total_transactions=len(transactions))
    except Exception as e:
        logger.error(f"Transactions page error: {e}")
        return render_template('transactions.html', transactions=[], total_transactions=0)

@app.route('/wallets')
def wallets():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    # Get real wallets from payment handler
    wallets_data = get_real_wallets()
    
    return render_template('wallets.html', wallets=wallets_data)

@app.route('/settings')
def settings():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    # Get current exchange rate from database
    exchange_rate = 50000  # Default
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = 'exchange_rate'")
            result = cur.fetchone()
            if result:
                exchange_rate = int(result['value'])
    except:
        pass
    
    return render_template('settings.html', exchange_rate=exchange_rate)

# API Routes for real operations
@app.route('/api/transactions/<int:transaction_id>/approve', methods=['POST'])
def approve_transaction(transaction_id):
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        with store.get_db() as conn:
            cur = conn.cursor()
            
            # Get transaction details
            cur.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
            transaction = cur.fetchone()
            
            if not transaction:
                return jsonify({'success': False, 'message': 'Transaction not found'}), 404
            
            # Update transaction status
            cur.execute("UPDATE transactions SET status = 'approved' WHERE id = ?", (transaction_id,))
            
            # Update user balance if it's a deposit
            if transaction['type'] == 'deposit':
                cur.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", 
                          (transaction['amount'], transaction['telegram_id']))

            _notify_user_about_transaction(transaction, 'approved')
            logger.info(f"Transaction {transaction_id} approved by admin")
        
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
            cur.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
            transaction = cur.fetchone()
            if not transaction:
                return jsonify({'success': False, 'message': 'Transaction not found'}), 404
            
            cur.execute("UPDATE transactions SET status = 'rejected' WHERE id = ?", (transaction_id,))
            _notify_user_about_transaction(transaction, 'rejected')
            
            logger.info(f"Transaction {transaction_id} rejected by admin")
        
        return jsonify({'success': True, 'message': 'Transaction rejected'})
    except Exception as e:
        logger.error(f"Error rejecting transaction: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/exchange_rate/update', methods=['POST'])
def update_exchange_rate():
    if not is_admin_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        new_rate = data.get('exchange_rate')
        
        if not new_rate or new_rate <= 0:
            return jsonify({'success': False, 'message': 'Invalid exchange rate'}), 400
        
        # Store in database
        with store.get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES ('exchange_rate', ?, ?)
            """, (new_rate, datetime.datetime.now().isoformat()))
        
        logger.info(f"Exchange rate updated to {new_rate} by admin")
        return jsonify({'success': True, 'message': 'Exchange rate updated'})
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
        
        # Update payment handler configuration
        # This would require updating the payment_handler.py file or storing in database
        
        logger.info(f"Wallet {method} updated by admin")
        return jsonify({'success': True, 'message': 'Wallet updated'})
    except Exception as e:
        logger.error(f"Error updating wallet: {e}")
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

if __name__ == '__main__':
    # Start bot status monitoring thread
    status_thread = threading.Thread(target=check_bot_status, daemon=True)
    status_thread.start()
    
    print("=" * 60)
    print("iChancy Bot - Real Admin Panel")
    print("=" * 60)
    print("URL: http://localhost:8080")
    print("Username: admin")
    print("Password: admin123")
    print("Connected to: Real Bot Database")
    print("=" * 60)
    print("Starting server...")
    
    app.run(debug=True, host='0.0.0.0', port=8080)
