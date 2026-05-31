"""
Supabase Database Client - Complete replacement for SQLite
All database operations now use Supabase exclusively
"""

import os
from datetime import datetime, timezone
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and Key must be set in environment variables")
        
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    def get_client(self):
        return self.client

# Global instance
supabase_client = SupabaseClient()

# =========================
# USER OPERATIONS
# =========================

def get_user_by_telegram_id(telegram_id):
    """Get user by Telegram ID"""
    try:
        result = supabase_client.client.table("users") \
            .select("*") \
            .eq("telegram_id", str(telegram_id)) \
            .maybe_single() \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error getting user {telegram_id}: {e}")
        return None

def create_user(telegram_id, username, first_name=None):
    """Create new user"""
    try:
        user_data = {
            "telegram_id": str(telegram_id),
            "username": username,
            "first_name": first_name,
            "balance_syp": 0,
            "balance_usd": 0,
            "is_blocked": False,
            "operations_count": 0,
            "total_deposits": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase_client.client.table("users") \
            .insert(user_data) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error creating user {telegram_id}: {e}")
        return None

def upsert_user(telegram_id, username, first_name=None):
    """Create or update user"""
    try:
        user_data = {
            "telegram_id": str(telegram_id),
            "username": username,
            "first_name": first_name,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase_client.client.table("users") \
            .upsert(user_data, on_conflict="telegram_id") \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error upserting user {telegram_id}: {e}")
        return None

def update_user_balance(telegram_id, new_balance_syp=None, new_balance_usd=None):
    """Update user balance"""
    try:
        update_data = {}
        if new_balance_syp is not None:
            update_data["balance_syp"] = new_balance_syp
        if new_balance_usd is not None:
            update_data["balance_usd"] = new_balance_usd
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = supabase_client.client.table("users") \
            .update(update_data) \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error updating balance for {telegram_id}: {e}")
        return None

def get_all_users(limit=100):
    """Get all users"""
    try:
        result = supabase_client.client.table("users") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error getting users: {e}")
        return []

# =========================
# TRANSACTION OPERATIONS
# =========================

def create_transaction(telegram_id, tx_type, amount, method="manual", 
                      transfer_num=None, status="pending", note=None):
    """Create new transaction"""
    try:
        tx_data = {
            "telegram_id": str(telegram_id),
            "type": tx_type,
            "method": method,
            "amount": float(amount),
            "transfer_num": transfer_num or "-",
            "status": status,
            "note": note or "",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase_client.client.table("transactions") \
            .insert(tx_data) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error creating transaction: {e}")
        return None

def get_user_transactions(telegram_id, tx_type=None, limit=50):
    """Get user transactions"""
    try:
        query = supabase_client.client.table("transactions") \
            .select("*") \
            .eq("telegram_id", str(telegram_id)) \
            .order("created_at", desc=True) \
            .limit(limit)
        
        if tx_type:
            query = query.eq("type", tx_type)
        
        result = query.execute()
        return result.data
    except Exception as e:
        print(f"Error getting transactions for {telegram_id}: {e}")
        return []

def get_transactions_by_type(tx_type, limit=100):
    """Get transactions by type"""
    try:
        result = supabase_client.client.table("transactions") \
            .select("*") \
            .eq("type", tx_type) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error getting {tx_type} transactions: {e}")
        return []

def update_transaction_status(transaction_id, status):
    """Update transaction status"""
    try:
        result = supabase_client.client.table("transactions") \
            .update({"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}) \
            .eq("id", transaction_id) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error updating transaction {transaction_id}: {e}")
        return None

def get_transaction_by_id(transaction_id):
    """Get transaction by ID"""
    try:
        result = supabase_client.client.table("transactions") \
            .select("*") \
            .eq("id", transaction_id) \
            .maybe_single() \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error getting transaction {transaction_id}: {e}")
        return None

# =========================
# TERMS SYSTEM
# =========================

def set_user_agreed_terms(telegram_id):
    """Set user as agreed to terms"""
    try:
        result = supabase_client.client.table("users") \
            .update({"agreed_terms": True, "updated_at": datetime.now(timezone.utc).isoformat()}) \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error setting terms agreement for {telegram_id}: {e}")
        return None

def has_user_agreed_terms(telegram_id):
    """Check if user agreed to terms"""
    try:
        result = supabase_client.client.table("users") \
            .select("agreed_terms") \
            .eq("telegram_id", str(telegram_id)) \
            .maybe_single() \
            .execute()
        
        if result.data:
            return result.data.get("agreed_terms", False)
        return False
    except Exception as e:
        print(f"Error checking terms agreement for {telegram_id}: {e}")
        return False

# =========================
# MESSAGE OPERATIONS
# =========================

def save_message(telegram_id, username, content, direction="incoming"):
    """Save message to database"""
    try:
        message_data = {
            "telegram_id": str(telegram_id),
            "username": username,
            "content": content,
            "direction": direction,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase_client.client.table("messages") \
            .insert(message_data) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error saving message: {e}")
        return None

def get_messages(limit=100):
    """Get messages"""
    try:
        result = supabase_client.client.table("messages") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error getting messages: {e}")
        return []

# =========================
# SETTINGS OPERATIONS
# =========================

def get_setting(key):
    """Get setting value"""
    try:
        result = supabase_client.client.table("settings") \
            .select("value") \
            .eq("key", key) \
            .maybe_single() \
            .execute()
        
        if result.data:
            return result.data.get("value")
        return None
    except Exception as e:
        print(f"Error getting setting {key}: {e}")
        return None

def update_setting(key, value):
    """Update setting"""
    try:
        result = supabase_client.client.table("settings") \
            .upsert({"key": key, "value": str(value)}, on_conflict="key") \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error updating setting {key}: {e}")
        return None

# =========================
# LOGGING OPERATIONS
# =========================

def log_event(event_type, message, telegram_id=None):
    """Log event to database"""
    try:
        log_data = {
            "type": event_type,
            "message": message,
            "telegram_id": str(telegram_id) if telegram_id else None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase_client.client.table("bot_logs") \
            .insert(log_data) \
            .execute()
        return result.data
    except Exception as e:
        print(f"Error logging event: {e}")
        return None
