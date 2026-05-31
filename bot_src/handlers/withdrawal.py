import Logger
import store
from services.iChancyAPI import iChancyAPI
from config.telegram import InlineKeyboardButton, InlineKeyboardMarkup
import handlers.payment_handler
from datetime import datetime

logger = Logger.getLogger()

# =========================
# الأزرار
# =========================
def getKeyboard(user_id):
    keyboard = [
        [
            InlineKeyboardButton("Syriatel Cash 🟢", callback_data='syriatel_cash_withdrawal'),
            InlineKeyboardButton("Bemo", callback_data='bemo_withdrawal'),
        ],
        [
            InlineKeyboardButton("Payeer", callback_data='payeer_withdrawal'),
            InlineKeyboardButton("حوالة", callback_data='hawala_withdrawal')
        ],
        [
            InlineKeyboardButton("Sham Cash (SYP) 🇸🇾", callback_data='sham_cash_syp_withdrawal')
        ],
        [
            InlineKeyboardButton("Sham Cash (USD) 💲", callback_data='sham_cash_usd_withdrawal')
        ],
        [
            InlineKeyboardButton("Coinex", callback_data='coinex_withdrawal'),
            InlineKeyboardButton("Cwallet", callback_data='cwallet_withdrawal')
        ],
        [
            InlineKeyboardButton("USDT Bep 20", callback_data='usdt_bep_20_withdrawal'),
            InlineKeyboardButton("USDT trc 20", callback_data='usdt_trc_20_withdrawal')
        ],
        [
            InlineKeyboardButton("القائمة الرئيسية", callback_data='back_to_menu')
        ],
    ]
    return keyboard


def getReplyMarkup(user_id):
    return InlineKeyboardMarkup(getKeyboard(user_id))


def getUserInfoText(user_id):
    return "اختر احد الطرق"


# =========================
# عرض قائمة السحب
# =========================
async def handle_withdrawal(update, context):
    query = update.callback_query
    user_id = update.effective_user.id

    await query.answer()

    logger.info("User Click on Withdrawal Option")

    message = "💸 **طرق السحب**\n\nاختر طريقة السحب المناسبة:"

    try:
        await query.edit_message_text(
            text=message,
            reply_markup=getReplyMarkup(user_id),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"edit_message_text error: {e}")

        try:
            await query.message.reply_text(
                text=message,
                reply_markup=getReplyMarkup(user_id),
                parse_mode='Markdown'
            )
        except Exception as e2:
            logger.error(f"reply fallback error: {e2}")
            await query.message.reply_text("⚠️ حدث خطأ في عرض طرق السحب. يرجى المحاولة لاحقاً")


# =========================
# مثال (مكان تنفيذ السحب الحقيقي)
# =========================
async def process_withdrawal_success(user_id, amount, method):
    """
    يتم استدعاؤها بعد نجاح عملية السحب الفعلية
    """

    try:
        # حفظ العملية
        store.add_transaction(user_id, "withdrawal", amount)

        # إرسال للوحة التحكم (Realtime)
        await broadcast({
            "type": "withdrawal",
            "payload": {
                "telegram_id": user_id,
                "amount": amount,
                "method": method,
                "time": datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Withdrawal process error: {e}")