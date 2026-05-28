import Logger
from telegram import Update
from telegram.ext import (
    ContextTypes,
)

logger = Logger.getLogger()

import logging
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    logger.error(f"🔥 ERROR: {context.error}", exc_info=True)

    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                f"❌ صار خطأ:\n{context.error}"
            )
    except Exception:
        logger.error("Failed to send error message to user")
