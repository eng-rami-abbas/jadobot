import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update, Bot, CallbackQuery

load_dotenv()

# Telegram Configuration
PARENT_ID = os.getenv("PARENT_ID", "2613607")
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "7179419936")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "https://t.me/jadobotichancy")

# Ichancy Platform Credentials
ICHANCY_USERNAME = os.getenv("ICHANCY_USERNAME", "jadobot@jado.nsp")
ICHANCY_PASSWORD = os.getenv("ICHANCY_PASSWORD", "Jado1993@@")
COOKIE_STRING = os.getenv("COOKIE_STRING")

# Railway/Webhook Configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "8080"))

def validate_tokens():
    """Validate that required tokens are set"""
    if not TOKEN:
        raise ValueError("Telegram bot token is not set in config.telegram.TOKEN")

    # COOKIE_STRING is no longer required - we authenticate via iChancyAPI
    # which uses ICHANCY_USERNAME and ICHANCY_PASSWORD environment variables

    # For webhook mode, validate webhook URL
    if os.getenv("RAILWAY_ENVIRONMENT") == "production" and not WEBHOOK_URL:
        raise ValueError("Webhook URL is not set in config.telegram.WEBHOOK_URL")

    return True