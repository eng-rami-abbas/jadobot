"""
Check bot pause status from Supabase app_settings (control panel).
"""
import time
import logging
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop

import supabase_integration as supa

logger = logging.getLogger(__name__)

_cache = {"status": "active", "message": "", "expires": 0.0}
CACHE_TTL_SEC = 8

ALWAYS_ALLOWED_CALLBACKS = {
    "check_sub",
    "agree",
    "reject",
    "terms_and_conditions",
}


def _refresh_cache():
    now = time.time()
    if now < _cache["expires"]:
        return
    try:
        client = supa.get_client()
        res = client.table("app_settings").select("key,value").in_(
            "key", ["bot_status", "bot_stop_message"]
        ).execute()
        settings = {row["key"]: row["value"] for row in (res.data or [])}
        _cache["status"] = settings.get("bot_status", "active")
        _cache["message"] = settings.get(
            "bot_stop_message",
            "⏸️ البوت متوقف مؤقتاً للصيانة. يرجى المحاولة لاحقاً.",
        )
    except Exception as e:
        logger.error(f"bot_status cache refresh error: {e}")
    _cache["expires"] = now + CACHE_TTL_SEC


def is_bot_paused() -> bool:
    _refresh_cache()
    return _cache["status"] == "paused"


def get_maintenance_message() -> str:
    _refresh_cache()
    return _cache["message"]


async def _reply_paused(update: Update):
    text = get_maintenance_message()
    if update.callback_query:
        try:
            await update.callback_query.answer(text, show_alert=True)
        except Exception:
            pass
        try:
            await update.callback_query.message.reply_text(text)
        except Exception:
            pass
    elif update.message:
        await update.message.reply_text(text)


async def bot_status_callback_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return
    data = update.callback_query.data or ""
    if data in ALWAYS_ALLOWED_CALLBACKS:
        return
    if is_bot_paused():
        await _reply_paused(update)
        raise ApplicationHandlerStop()


async def bot_status_message_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.message.text and update.message.text.startswith("/"):
        cmd = update.message.text.split()[0].lower()
        if cmd in ("/start", "/cancel"):
            return
    if is_bot_paused():
        await _reply_paused(update)
        raise ApplicationHandlerStop()
