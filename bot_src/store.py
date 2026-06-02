"""
store.py - طبقة البيانات (Supabase فقط)
تم تحويل هذا الملف من SQLite إلى Supabase بالكامل
جميع العمليات تمر عبر supabase_integration.py
"""
import logging
from datetime import datetime, timezone

import supabase_integration as supa

logger = logging.getLogger(__name__)


# =========================
# USERS
# =========================

def getUserByTelegramId(telegram_id):
    """الحصول على بيانات المستخدم عبر معرف تيلغرام"""
    try:
        client = supa.get_client()
        res = client.table("users") \
            .select("*") \
            .eq("telegram_id", str(telegram_id)) \
            .maybe_single() \
            .execute()
        return res.data if res.data else None
    except Exception as e:
        logger.error(f"getUserByTelegramId error: {e}")
        return None


def updateUser(telegram_id, fields):
    """تحديث بيانات المستخدم"""
    if not fields:
        return False
    try:
        client = supa.get_client()
        res = client.table("users") \
            .update(fields) \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
        return bool(res.data)
    except Exception as e:
        logger.error(f"updateUser error: {e}")
        return False


def setUserState(telegram_id, state):
    """تعيين حالة المستخدم"""
    try:
        client = supa.get_client()
        # التأكد من وجود المستخدم أولاً
        user = getUserByTelegramId(telegram_id)
        if not user:
            supa.upsert_user(
                telegram_id=int(telegram_id),
                username="",
                first_name="",
                last_name=""
            )
        client.table("users") \
            .update({"state": state}) \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
    except Exception as e:
        logger.error(f"setUserState error: {e}")


def getUserState(telegram_id):
    """الحصول على حالة المستخدم"""
    try:
        user = getUserByTelegramId(telegram_id)
        if user:
            return user.get("state")
    except Exception as e:
        logger.error(f"getUserState error: {e}")
    return None


def deleteUser(telegram_id):
    """حذف المستخدم"""
    try:
        client = supa.get_client()
        res = client.table("users") \
            .delete() \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
        return bool(res.data)
    except Exception as e:
        logger.error(f"deleteUser error: {e}")
        return False


def insertNewUser(telegram_id, username):
    """إدراج مستخدم جديد أو تحديثه"""
    try:
        supa.upsert_user(
            telegram_id=int(telegram_id),
            username=username or "",
            first_name="",
            last_name=""
        )
    except Exception as e:
        logger.error(f"insertNewUser error: {e}")


# =========================
# TRANSACTIONS
# =========================

def insertTransaction(telegram_id, value, action_type, provider_type, transfer_num):
    """إدراج معاملة جديدة"""
    try:
        client = supa.get_client()
        res = client.table("transactions").insert({
            "telegram_id": str(telegram_id),
            "type": action_type,
            "method": provider_type,
            "amount_syp": value,
            "wallet_address": transfer_num,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        if res.data and len(res.data) > 0:
            return res.data[0].get("id")
        return None
    except Exception as e:
        logger.error(f"insertTransaction error: {e}")
        return None


def add_transaction(user_id, type_, amount):
    """إضافة معاملة يدوية"""
    return insertTransaction(user_id, amount, type_, "manual", "-")


def get_user_transactions(telegram_id, tx_type=None):
    """الحصول على معاملات المستخدم"""
    try:
        client = supa.get_client()
        query = client.table("transactions") \
            .select("*") \
            .eq("telegram_id", str(telegram_id)) \
            .order("created_at", desc=True)

        if tx_type:
            query = query.eq("type", tx_type)

        res = query.execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"get_user_transactions error: {e}")
        return []


# =========================
# ADMIN / DASHBOARD APIs
# =========================

def get_all_users(limit=100):
    """الحصول على جميع المستخدمين"""
    try:
        client = supa.get_client()
        res = client.table("users") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"get_all_users error: {e}")
        return []


def get_transactions_by_type(tx_type):
    """الحصول على المعاملات حسب النوع"""
    try:
        client = supa.get_client()
        res = client.table("transactions") \
            .select("*") \
            .eq("type", tx_type) \
            .order("created_at", desc=True) \
            .limit(100) \
            .execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"get_transactions_by_type error: {e}")
        return []


# =========================
# UPDATE STATUS
# =========================

def update_transaction_status(transaction_id, transaction_type, status):
    """تحديث حالة المعاملة"""
    try:
        client = supa.get_client()
        client.table("transactions") \
            .update({"status": status}) \
            .eq("id", transaction_id) \
            .eq("type", transaction_type) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"update_transaction_status error: {e}")
        return False


def get_transaction_by_id(transaction_id, transaction_type):
    """الحصول على معاملة بالمعرف والنوع"""
    try:
        client = supa.get_client()
        res = client.table("transactions") \
            .select("*") \
            .eq("id", transaction_id) \
            .eq("type", transaction_type) \
            .maybe_single() \
            .execute()
        return res.data if res.data else None
    except Exception as e:
        logger.error(f"get_transaction_by_id error: {e}")
        return None


# =========================
# BALANCE
# =========================

def update_user_balance(telegram_id, new_balance):
    """تحديث رصيد المستخدم"""
    try:
        supa.update_user_balance(telegram_id, new_balance)
    except Exception as e:
        logger.error(f"update_user_balance error: {e}")


def get_user_balance(telegram_id):
    """الحصول على رصيد المستخدم"""
    return supa.get_user_balance(telegram_id)


# =========================
# TERMS SYSTEM
# =========================

def set_user_agreed(telegram_id: int):
    """تسجيل موافقة المستخدم على الشروط"""
    try:
        supa.upsert_user(
            telegram_id=telegram_id,
            username="",
            first_name="",
            last_name=""
        )
        client = supa.get_client()
        client.table("users") \
            .update({"agreed_terms": True}) \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
    except Exception as e:
        logger.error(f"set_user_agreed error: {e}")


def has_user_agreed(telegram_id: int) -> bool:
    """التحقق من موافقة المستخدم على الشروط"""
    try:
        user = getUserByTelegramId(telegram_id)
        if user:
            return bool(user.get("agreed_terms", False))
    except Exception as e:
        logger.error(f"has_user_agreed error: {e}")
    return False


# =========================
# MESSAGE SYSTEM
# =========================

def insertMessageToAdmin(telegram_id, message):
    """إدراج رسالة للأدمن"""
    try:
        supa.save_message(telegram_id, "", message, "to_admin")
    except Exception as e:
        logger.error(f"insertMessageToAdmin error: {e}")


# =========================
# LEGACY FUNCTIONS (for backward compatibility)
# =========================

def getDatabaseConnection():
    """دالة متوافقة مع الإصدارات السابقة - لم تعد تستخدم SQLite"""
    return None


def init_db():
    """دالة متوافقة مع الإصدارات السابقة - لم تعد تحتاج SQLite"""
    pass


def getUserIdByTelegramId(telegram_id):
    """الحصول على معرف المستخدم الداخلي"""
    try:
        user = getUserByTelegramId(telegram_id)
        if user:
            return {"id": user.get("id")}
    except Exception as e:
        logger.error(f"getUserIdByTelegramId error: {e}")
    return None


def insertNewBalance(telegram_id, new_balance):
    """تحديث رصيد المستخدم (متوافق مع الإصدارات السابقة)"""
    try:
        supa.update_user_balance(telegram_id, new_balance)
    except Exception as e:
        logger.error(f"insertNewBalance error: {e}")


def insertNewAccountBalance(telegram_id, new_account_balance):
    """تحديث رصيد حساب iChancy للمستخدم"""
    try:
        client = supa.get_client()
        client.table("users") \
            .update({"account_balance": new_account_balance}) \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
    except Exception as e:
        logger.error(f"insertNewAccountBalance error: {e}")


def update_user_account_balance(user_id, new_account_balance):
    """تحديث رصيد حساب المستخدم بمعرف المستخدم الداخلي"""
    try:
        client = supa.get_client()
        client.table("users") \
            .update({"account_balance": new_account_balance}) \
            .eq("id", user_id) \
            .execute()
    except Exception as e:
        logger.error(f"update_user_account_balance error: {e}")


def insertInTransactionAccount(user_id, status, tx_type, value=0):
    """إدراج معاملة حساب"""
    try:
        client = supa.get_client()
        client.table("transactions").insert({
            "user_id": str(user_id),
            "type": tx_type,
            "amount_syp": abs(value),
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"insertInTransactionAccount error: {e}")


# =========================
# ADMIN FUNCTIONS (used by admin_handler.py)
# =========================

def getUserById(user_id):
    """الحصول على بيانات المستخدم عبر المعرف الداخلي"""
    try:
        client = supa.get_client()
        res = client.table("users") \
            .select("*") \
            .eq("id", user_id) \
            .maybe_single() \
            .execute()
        if res.data:
            # Convert dict to tuple-like list for backward compatibility
            d = res.data
            return [
                d.get("id"),
                d.get("telegram_id"),
                d.get("username", ""),
                d.get("first_name", ""),
                d.get("last_name", ""),
                d.get("balance_syp", 0),
                d.get("created_at", ""),
            ]
        return None
    except Exception as e:
        logger.error(f"getUserById error: {e}")
        return None


def get_pending_transactions(limit=20):
    """الحصول على المعاملات المعلقة"""
    try:
        client = supa.get_client()
        res = client.table("transactions") \
            .select("*") \
            .eq("status", "pending") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"get_pending_transactions error: {e}")
        return []


def ban_user(telegram_id):
    """حظر مستخدم"""
    try:
        client = supa.get_client()
        client.table("users") \
            .update({"is_blocked": True}) \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"ban_user error: {e}")
        return False


def unban_user(telegram_id):
    """إلغاء حظر مستخدم"""
    try:
        client = supa.get_client()
        client.table("users") \
            .update({"is_blocked": False}) \
            .eq("telegram_id", str(telegram_id)) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"unban_user error: {e}")
        return False


def get_user_count():
    """الحصول على عدد المستخدمين"""
    try:
        client = supa.get_client()
        res = client.table("users") \
            .select("id", count="exact") \
            .execute()
        return res.count if hasattr(res, 'count') else len(res.data or [])
    except Exception as e:
        logger.error(f"get_user_count error: {e}")
        return 0


def get_recent_transactions(limit=10):
    """الحصول على آخر المعاملات"""
    try:
        client = supa.get_client()
        res = client.table("transactions") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"get_recent_transactions error: {e}")
        return []
