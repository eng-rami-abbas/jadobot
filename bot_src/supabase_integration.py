import os
import logging
from datetime import datetime, timezone
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://kpnxtvargeajpxgswdso.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_client: Client = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# =========================
# 🔥 EXCHANGE RATE
# =========================
def get_exchange_rate() -> float:
    try:
        res = get_client().table("app_settings").select("value").eq("key", "exchange_rate").execute()
        if res.data and len(res.data) > 0:
            return float(res.data[0]["value"])
    except Exception as e:
        logger.error(f"get_exchange_rate error: {e}")
    return 13000.0


# =========================
# 🔥 WALLET SYSTEM
# =========================

def get_active_wallets() -> list:
    try:
        res = get_client().table("wallets") \
            .select("*") \
            .eq("is_active", True) \
            .order("sort_order") \
            .execute()

        return res.data or []
    except Exception as e:
        logger.error(f"get_active_wallets error: {e}")
    return []


def get_wallet_by_key(wallet_key: str) -> dict:
    try:
        res = get_client().table("wallets") \
            .select("*") \
            .eq("key", wallet_key) \
            .execute()

        data = res.data or []
        return data[0] if data else {}

    except Exception as e:
        logger.error(f"get_wallet_by_key error: {e}")
        return {}


def create_wallet(data: dict):
    try:
        return get_client().table("wallets").insert(data).execute()
    except Exception as e:
        logger.error(f"create_wallet error: {e}")


def update_wallet(wallet_id: str, data: dict):
    try:
        return get_client().table("wallets").update(data).eq("id", wallet_id).execute()
    except Exception as e:
        logger.error(f"update_wallet error: {e}")


# =========================
# USERS (بدون تغيير)
# =========================

def is_user_blocked(telegram_id: int) -> bool:
    try:
        res = get_client().table("users") \
            .select("is_blocked") \
            .eq("telegram_id", telegram_id) \
            .execute()

        data = res.data or []
        if data:
            return bool(data[0].get("is_blocked", False))

    except Exception as e:
        logger.error(f"is_user_blocked error: {e}")

    return False


def upsert_user(telegram_id: int, username: str, first_name: str = "", last_name: str = ""):
    try:
        user_data = {
            "telegram_id": str(telegram_id),
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "last_active": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }
            
        get_client().table("users").upsert(user_data, on_conflict="telegram_id").execute()
    except Exception as e:
        logger.error(f"upsert_user error: {e}")


def get_ichancy_details_by_telegram_id(telegram_id):
    """Get iChancy account details for a Telegram user."""
    try:
        result = get_client().table("users_ichancy_details") \
            .select("*") \
            .eq("telegram_id", str(telegram_id)) \
            .maybe_single() \
            .execute()
        return result.data
    except Exception as e:
        logger.error(f"get_ichancy_details_by_telegram_id error: {e}")
        return None


def upsert_ichancy_details(telegram_id, username, email, password, player_id, extra=None):
    """Insert or update the user's iChancy account details."""
    try:
        account_data = {
            "telegram_id": str(telegram_id),
            "username": username,
            "email": email,
            "password": password,
            "player_id": str(player_id) if player_id is not None else "0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if extra and isinstance(extra, dict):
            account_data.update(extra)

        return get_client().table("users_ichancy_details").upsert(account_data, on_conflict="telegram_id").execute()
    except Exception as e:
        logger.error(f"upsert_ichancy_details error: {e}")
        return None


# =========================
# MESSAGES (بدون تغيير)
# =========================

def save_message(telegram_id: int, username: str, content: str, direction: str = "incoming"):
    try:
        get_client().table("messages").insert({
            "telegram_id": telegram_id,
            "username": username,
            "content": content,
            "direction": direction,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"save_message error: {e}")


# =========================
# 🔥 DEPOSITS
# =========================

def insert_deposit(
    telegram_id: int,
    username: str,
    amount_syp: float,
    transaction_id: str,
    wallet_name: str
) -> str:
    """
    Create a new deposit transaction.
    Returns the operation_number as confirmation.
    """
    logger.info(f"📝 insert_deposit called: telegram_id={telegram_id}, amount={amount_syp}, wallet={wallet_name}")

    try:
        # ضرب المبلغ في 100 (تحويل من ل.س إلى فئات أصغر)
        final_amount = amount_syp * 100

        # Get exchange rate
        exchange_rate = get_exchange_rate()
        amount_usd = final_amount / exchange_rate if exchange_rate > 0 else 0

        # Get user_id if exists
        user_res = get_client().table("users") \
            .select("id") \
            .eq("telegram_id", telegram_id) \
            .execute()
        user_id = user_res.data[0].get("id") if user_res.data and len(user_res.data) > 0 else None

        logger.info(f"👤 User ID: {user_id}, Exchange rate: {exchange_rate}")

        # Insert transaction
        res = get_client().table("transactions").insert({
            "user_id": user_id,
            "telegram_id": telegram_id,
            "username": username,
            "type": "deposit",
            "amount_syp": final_amount,
            "amount_usd": amount_usd,
            "exchange_rate": exchange_rate,
            "status": "pending",
            "wallet_name": wallet_name,
            "wallet_address": transaction_id,
            "notes": f"Transaction ID: {transaction_id}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        logger.info(f"✅ Supabase response: {res.data}")

        # Get operation number
        if res.data and len(res.data) > 0:
            op_num = res.data[0].get("operation_number")
            logger.info(f"✅ Deposit inserted: op={op_num}, original={amount_syp}, final={final_amount}")

            # 🔥 تسجيل في transaction_logs
            try:
                log_data = {
                    "telegram_id": telegram_id,
                    "username": username,
                    "type": "deposit",
                    "amount_syp": int(final_amount),
                    "status": "pending",
                    "wallet_name": wallet_name,
                    "operation_number": op_num,
                    "notes": f"Original: {amount_syp}, TxID: {transaction_id}",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                logger.info(f"📝 Attempting to log to transaction_logs: {log_data}")

                log_res = get_client().table("transaction_logs").insert(log_data).execute()
                logger.info(f"✅ Logged to transaction_logs: deposit op={op_num}, response: {log_res.data}")
            except Exception as log_err:
                logger.error(f"⚠️ Failed to log to transaction_logs: {log_err}")
                logger.error(f"⚠️ Error type: {type(log_err)}")

            # 🔥 إدراج في جدول deposits للتحقق من أهلية عجلة الحظ
            try:
                get_client().table("deposits").insert({
                    "user_id": str(telegram_id),
                    "amount": amount_syp,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
                logger.info(f"✅ Inserted into deposits table for user {telegram_id}")
            except Exception as dep_err:
                logger.error(f"⚠️ Failed to insert into deposits table: {dep_err}")

            return str(op_num)

        logger.warning("⚠️ No data returned from Supabase insert")
        return "pending"

    except Exception as e:
        logger.error(f"❌ insert_deposit error: {e}")
        raise


def get_user_balance(telegram_id) -> float:
    """Get user current balance."""
    try:
        client = get_client()
        for tid in (telegram_id, str(telegram_id), int(telegram_id) if str(telegram_id).isdigit() else None):
            if tid is None:
                continue
            res = client.table("users").select("balance_syp").eq("telegram_id", tid).execute()
            if res.data:
                return float(res.data[0].get("balance_syp", 0))
        return 0
    except Exception as e:
        logger.error(f"get_user_balance error: {e}")
        return 0


def update_user_balance(telegram_id, new_balance: float):
    """Update user balance."""
    try:
        client = get_client()
        for tid in (telegram_id, str(telegram_id), int(telegram_id) if str(telegram_id).isdigit() else None):
            if tid is None:
                continue
            res = client.table("users").update({"balance_syp": new_balance}).eq("telegram_id", tid).execute()
            if res.data:
                logger.info(f"Updated balance for {telegram_id}: {new_balance}")
                return res
        raise RuntimeError(f"User not found for telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"update_user_balance error: {e}")
        raise


def get_bot_status() -> str:
    try:
        res = get_client().table("app_settings").select("value").eq("key", "bot_status").execute()
        if res.data:
            return res.data[0].get("value", "active")
    except Exception as e:
        logger.error(f"get_bot_status error: {e}")
    return "active"


def is_bot_paused() -> bool:
    return get_bot_status() == "paused"


def has_deposited_today(telegram_id) -> bool:
    """At least one completed deposit today (Asia/Damascus calendar day)."""
    try:
        import pytz
        tz = pytz.timezone("Asia/Damascus")
        today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        client = get_client()
        for tid in (int(telegram_id), str(telegram_id), telegram_id):
            res = client.table("transactions") \
                .select("id") \
                .eq("type", "deposit") \
                .eq("status", "completed") \
                .eq("telegram_id", tid) \
                .gte("created_at", today_start.isoformat()) \
                .limit(1) \
                .execute()
            if res.data:
                return True
        return False
    except Exception as e:
        logger.error(f"has_deposited_today error: {e}")
        return False


# =========================
# 🔥 NOTIFICATIONS SYSTEM
# =========================

def get_pending_notifications() -> list:
    """Get pending notifications to be sent via Telegram."""
    try:
        res = get_client().table("pending_notifications") \
            .select("*") \
            .eq("status", "pending") \
            .order("created_at") \
            .execute()
        return res.data or []
    except Exception as e:
        logger.error(f"get_pending_notifications error: {e}")
        return []


def mark_notification_sent(notification_id: str, error: str = None):
    """Mark notification as sent or failed."""
    try:
        status = "failed" if error else "sent"
        data = {
            "status": status,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }
        if error:
            data["error_message"] = error
        
        get_client().table("pending_notifications") \
            .update(data) \
            .eq("id", notification_id) \
            .execute()
    except Exception as e:
        logger.error(f"mark_notification_sent error: {e}")


def add_notification(telegram_id: int, message: str):
    """Add a new notification to be sent."""
    try:
        get_client().table("pending_notifications").insert({
            "telegram_id": telegram_id,
            "message": message,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        logger.info(f"Notification added for user {telegram_id}")
    except Exception as e:
        logger.error(f"add_notification error: {e}")


def get_notification_message(message_type: str) -> str:
    """Get customizable notification message from app_settings."""
    try:
        key_map = {
            "deposit_approved": "deposit_approved_message",
            "deposit_rejected": "deposit_rejected_message"
        }
        key = key_map.get(message_type, message_type)
        
        res = get_client().table("app_settings") \
            .select("value") \
            .eq("key", key) \
            .execute()
        
        if res.data and len(res.data) > 0:
            return res.data[0].get("value", "")
        
        # Default messages
        defaults = {
            "deposit_approved_message": "✅ تمت الموافقة على إيداعك!\n\n💰 المبلغ: {amount_syp} ل.س\n🏦 المحفظة: {wallet_name}\n📊 رقم العملية: {operation_number}",
            "deposit_rejected_message": "❌ تم رفض إيداعك\n\n💰 المبلغ: {amount_syp} ل.س\n🏦 المحفظة: {wallet_name}\n📊 رقم العملية: {operation_number}\n\nيرجى التواصل مع الدعم."
        }
        return defaults.get(key, "")
    except Exception as e:
        logger.error(f"get_notification_message error: {e}")
        return ""


# =========================
# 🔥 WITHDRAWAL METHODS
# =========================
def get_active_withdrawal_methods():
    """الحصول على طرق السحب النشطة"""
    try:
        res = get_client().table("withdrawal_methods") \
            .select("*") \
            .eq("is_active", True) \
            .order("sort_order") \
            .execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"get_active_withdrawal_methods error: {e}")
        return []


def get_withdrawal_method_by_key(key: str):
    """الحصول على طريقة سحب بالمفتاح"""
    try:
        logger.info(f"Looking for withdrawal method with key: {key}")
        res = get_client().table("withdrawal_methods") \
            .select("*") \
            .eq("key", key) \
            .eq("is_active", True) \
            .execute()
        logger.info(f"Query result for key {key}: {res.data}")
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"get_withdrawal_method_by_key error for key {key}: {e}")
        return None


def get_withdrawal_fee_percentage() -> float:
    """الحصول على نسبة خصم السحب"""
    try:
        res = get_client().table("app_settings") \
            .select("value") \
            .eq("key", "withdrawal_fee_percentage") \
            .execute()
        if res.data and len(res.data) > 0:
            return float(res.data[0]["value"])
        return 5.0  # Default 5%
    except Exception as e:
        logger.error(f"get_withdrawal_fee_percentage error: {e}")
        return 5.0


def insert_withdrawal(telegram_id: int, username: str, amount_syp: float, 
                       account_number: str, method_key: str, fee_amount: float = 0):
    """إدخال طلب سحب جديد"""
    try:
        final_amount = int(amount_syp * 100)  # Convert to internal units
        
        res = get_client().table("transactions").insert({
            "telegram_id": telegram_id,
            "username": username,
            "type": "withdrawal",
            "amount": final_amount,
            "amount_syp": amount_syp,
            "account_number": account_number,
            "method": method_key,
            "fee_amount": int(fee_amount * 100),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        logger.info(f"✅ Withdrawal inserted: {res.data}")

        # إرجاع operation_number إذا موجود، وإلا id
        if res.data and len(res.data) > 0:
            op_num = res.data[0].get("operation_number")
            result_id = op_num if op_num else res.data[0].get("id")

            # 🔥 تسجيل في transaction_logs
            try:
                get_client().table("transaction_logs").insert({
                    "telegram_id": telegram_id,
                    "username": username,
                    "type": "withdrawal",
                    "amount_syp": int(final_amount),
                    "status": "pending",
                    "wallet_name": method_key,
                    "operation_number": op_num,
                    "notes": f"Original: {amount_syp}, Account: {account_number}",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
                logger.info(f"✅ Logged to transaction_logs: withdrawal op={op_num}")
            except Exception as log_err:
                logger.error(f"⚠️ Failed to log to transaction_logs: {log_err}")

            return result_id
        return None
    except Exception as e:
        logger.error(f"❌ insert_withdrawal error: {e}")
        return None


# =========================
# 🔥 LOG EVENT
# =========================
def log_event(event_type: str, telegram_id: int, username: str, details: dict = None):
    """Log an event to the database"""
    try:
        data = {
            "event_type": event_type,
            "telegram_id": telegram_id,
            "username": username,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if details:
            data["details"] = details
        get_client().table("events").insert(data).execute()
    except Exception as e:
        logger.error(f"log_event error: {e}")


# =========================
# 🔥 WHEEL SPIN SYSTEM
# =========================
def get_wheel_last_spin(telegram_id: str) -> str:
    """Get last spin timestamp for a user"""
    try:
        res = get_client().table("wheel_spins") \
            .select("last_spin_at") \
            .eq("telegram_id", telegram_id) \
            .maybe_single() \
            .execute()
        if res.data:
            return res.data.get("last_spin_at")
        return None
    except Exception as e:
        logger.error(f"get_wheel_last_spin error: {e}")
        return None


def set_wheel_last_spin(telegram_id: str, spin_time: str, pending_bonus_percent: float = None):
    """Set last spin timestamp for a user; optionally store wheel bonus for next deposit."""
    try:
        row = {
            "telegram_id": str(telegram_id),
            "last_spin_at": spin_time,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if pending_bonus_percent is not None:
            row["pending_bonus_percent"] = float(pending_bonus_percent)
        get_client().table("wheel_spins").upsert(row, on_conflict="telegram_id").execute()
    except Exception as e:
        logger.error(f"set_wheel_last_spin error: {e}")


def get_pending_wheel_bonus(telegram_id) -> float:
    try:
        res = get_client().table("wheel_spins") \
            .select("pending_bonus_percent") \
            .eq("telegram_id", str(telegram_id)) \
            .maybe_single() \
            .execute()
        if res.data:
            return float(res.data.get("pending_bonus_percent") or 0)
    except Exception as e:
        logger.error(f"get_pending_wheel_bonus error: {e}")
    return 0.0


def clear_pending_wheel_bonus(telegram_id):
    try:
        get_client().table("wheel_spins") \
            .update({"pending_bonus_percent": 0}) \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
    except Exception as e:
        logger.error(f"clear_pending_wheel_bonus error: {e}")


def get_wheel_extra_spins(telegram_id) -> int:
    try:
        res = get_client().table("wheel_spins") \
            .select("extra_spins") \
            .eq("telegram_id", str(telegram_id)) \
            .maybe_single() \
            .execute()
        if res.data:
            return int(res.data.get("extra_spins") or 0)
    except Exception as e:
        logger.error(f"get_wheel_extra_spins error: {e}")
    return 0


def set_wheel_extra_spins(telegram_id, count: int):
    try:
        get_client().table("wheel_spins").upsert({
            "telegram_id": str(telegram_id),
            "extra_spins": max(0, int(count)),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="telegram_id").execute()
    except Exception as e:
        logger.error(f"set_wheel_extra_spins error: {e}")
