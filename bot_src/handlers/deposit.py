from telegram.ext import CallbackQueryHandler, ConversationHandler, MessageHandler, filters
import supabase_integration as supa
import Logger
from utils import helpers

logger = Logger.getLogger()

# =========================
# 📌 حالات المحادثة
# =========================
WALLET_SELECT, TRANSACTION_ID, AMOUNT, CONFIRM = range(4)

wallet_states = {}


# =========================
# 📌 عرض المحافظ (ديناميكي)
# =========================
async def handle_deposit(update, context):
    query = update.callback_query
    await query.answer()

    wallets = [w for w in supa.get_active_wallets() if w.get("key")]

    if not wallets:
        await query.edit_message_text("❌ لا توجد محافظ حالياً")
        return ConversationHandler.END

    keyboard = []

    for w in wallets:
        # 🔥 عرض اسم المحفظة فقط بدون إيموجي
        keyboard.append([
            {
                "text": w.get('name'),
                "callback_data": f"{w.get('key')}_deposit"
            }
        ])

    # 🔥 زر رجوع
    keyboard.append([
        {
            "text": "🔙 رجوع",
            "callback_data": "back_to_main"
        }
    ])

    try:
        # محاولة تعديل الرسالة
        await query.edit_message_text(
            "🏦 اختر طريقة الإيداع:",
            reply_markup={"inline_keyboard": keyboard}
        )
    except Exception as e:
        # إذا كانت الرسالة متطابقة، تجاهل الخطأ (لا تفعل شيئاً)
        if "not modified" in str(e).lower():
            pass  # الرسالة موجودة بالفعل، لا شيء يجب عمله
        else:
            logger.error(f"handle_deposit edit error: {e}")

    return WALLET_SELECT


# =========================
# 📌 اختيار محفظة
# =========================
async def wallet_selected(update, context):
    query = update.callback_query
    await query.answer()

    key = query.data.rsplit("_deposit", 1)[0]
    logger.info(f"Wallet selected: key={key}")

    wallet = supa.get_wallet_by_key(key)

    if not wallet:
        logger.error(f"Wallet not found for key: {key}")
        await query.edit_message_text("❌ المحفظة غير موجودة")
        return ConversationHandler.END

    user_id = update.effective_user.id
    logger.info(f"User {user_id} selected wallet: {wallet.get('name')}")

    wallet_states[user_id] = {
        "wallet": wallet,
        "step": "transaction_id"
    }

    wallet_number = wallet.get("wallet_number", "")
    header_text = wallet.get('header_text', '')  # 🔥 النص الأول
    message_template = wallet.get('message_template', '')  # 🔥 النص الثاني

    # 🔥 بناء الرسالة: النص الأول + رقم المحفظة + النص الثاني
    msg_parts = []
    if header_text:
        msg_parts.append(header_text)
    # 🔥 رقم المحفظة في المنتصف (قابل للنسخ)
    msg_parts.append(f"`{wallet_number}`")
    if message_template:
        # استبدال المتغيرات في القالب
        second_text = message_template.replace('{wallet_number}', wallet_number)
        msg_parts.append(second_text)
    else:
        # النص الافتراضي للنص الثاني
        msg_parts.append("✏️ أدخل **رقم عملية التحويل**:")

    msg = "\n\n".join(msg_parts)

    image_url = wallet.get("image_url")
    logger.info(f"Wallet image_url: {image_url}")

    try:
        if image_url:
            await query.message.reply_photo(
                photo=image_url,
                caption=msg,
                parse_mode="Markdown"
            )
            logger.info(f"Photo sent to user {user_id}")
        else:
            await query.edit_message_text(msg, parse_mode="Markdown")
            logger.info(f"Text message edited for user {user_id}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        # Try sending simple text as fallback
        try:
            await query.message.reply_text(msg, parse_mode="Markdown")
            logger.info(f"Fallback text sent to user {user_id}")
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")

    logger.info(f"Returning TRANSACTION_ID state for user {user_id}")
    return TRANSACTION_ID


# =========================
# � إدخال رقم العملية
# =========================
async def get_transaction_id(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    logger.info(f"get_transaction_id called by user {user_id}, entered: {text}")

    if user_id not in wallet_states:
        logger.error(f"User {user_id} not in wallet_states!")
        await update.message.reply_text("❌ انتهت الجلسة. ابدأ من جديد.")
        return ConversationHandler.END

    # حفظ رقم العملية
    wallet_states[user_id]["transaction_id"] = text
    wallet_states[user_id]["step"] = "amount"

    await update.message.reply_text(
        "💰 الآن أدخل **المبلغ** الذي قمت بإرساله (بالليرة السورية):",
        parse_mode="Markdown"
    )
    logger.info(f"Moving to AMOUNT state for user {user_id}")
    return AMOUNT


# =========================
# 💰 إدخال المبلغ
# =========================
async def get_amount(update, context):
    user_id = update.effective_user.id
    logger.info(f"get_amount called by user {user_id}")

    if user_id not in wallet_states:
        logger.error(f"User {user_id} not in wallet_states!")
        await update.message.reply_text("❌ انتهت الجلسة. ابدأ من جديد.")
        return ConversationHandler.END

    text = update.message.text
    logger.info(f"User {user_id} entered: {text}")

    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        logger.info(f"Parsed amount: {amount}")
    except:
        logger.error(f"Invalid number: {text}")
        await update.message.reply_text("❌ رقم غير صحيح. أدخل رقماً صحيحاً:")
        return AMOUNT

    state = wallet_states[user_id]
    wallet = state["wallet"]
    transaction_id = state.get("transaction_id", "manual")

    # حفظ المبلغ في الحالة
    state["amount"] = amount
    state["step"] = "confirm"

    # عرض رسالة التأكيد
    emoji = wallet.get('emoji') or '💳'
    confirm_msg = f"""
{emoji} **تأكيد الإيداع**

🏦 المحفظة: {wallet.get('title') or wallet.get('name')}
🔢 رقم العملية: `{transaction_id}`
💰 المبلغ: {amount:,.0f} ل.س

هل تريد تأكيد الإيداع؟
"""

    keyboard = [
        [{"text": "✅ تأكيد", "callback_data": "confirm_deposit"}],
        [{"text": "❌ إلغاء", "callback_data": "cancel_deposit"}]
    ]

    await update.message.reply_text(
        confirm_msg,
        parse_mode="Markdown",
        reply_markup={"inline_keyboard": keyboard}
    )
    logger.info(f"Returning CONFIRM state for user {user_id}")
    return CONFIRM


# =========================
# ✅ تأكيد أو إلغاء الإيداع
# =========================
async def confirm_deposit(update, context):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    logger.info(f"confirm_deposit called by user {user_id}, data={data}")

    if user_id not in wallet_states:
        await query.edit_message_text("❌ انتهت الجلسة. ابدأ من جديد.")
        return ConversationHandler.END

    state = wallet_states[user_id]
    wallet = state["wallet"]
    amount = state["amount"]
    transaction_id = state.get("transaction_id", "manual")

    if data == "cancel_deposit":
        del wallet_states[user_id]
        await query.edit_message_text("❌ تم إلغاء الإيداع.")
        return ConversationHandler.END

    # تأكيد الإيداع
    try:
        result = supa.insert_deposit(
            telegram_id=user_id,
            username=update.effective_user.username or str(user_id),
            amount_syp=amount,
            transaction_id=transaction_id,
            wallet_name=wallet.get("key") or wallet.get("name")
        )
        logger.info(f"Deposit inserted successfully: {result}")

        del wallet_states[user_id]

        await query.edit_message_text(
            f"✅ تم إرسال طلب الإيداع\n\n"
            f"🏦 {wallet.get('name')}\n"
            f"💰 {amount:,.0f} ل.س\n"
            f"🔢 رقم العملية: {transaction_id}\n"
            f"📋 رقم الطلب: {result}\n\n"
            f"⏳ في انتظار الموافقة..."
        )
    except Exception as e:
        logger.error(f"insert_deposit failed: {e}")
        await query.edit_message_text(f"❌ خطأ في حفظ الإيداع: {e}")

    return ConversationHandler.END


# =========================
# ❌ إلغاء
# =========================
async def cancel(update, context):
    wallet_states.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ تم الإلغاء")
    return ConversationHandler.END


# =========================
# 🔙 رجوع للقائمة الرئيسية
# =========================
async def back_to_main(update, context):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    wallet_states.pop(user_id, None)

    try:
        # تعديل الرسالة لإظهار القائمة الرئيسية
        await query.edit_message_text(
            helpers.getTextWelcome(update.effective_user.username or ""),
            reply_markup=helpers.getReplyMarkup(user_id),
            parse_mode='Markdown'
        )
    except Exception as e:
        # إذا كانت الرسالة متطابقة أو أي خطأ آخر، أرسل رسالة جديدة
        if "not modified" in str(e).lower():
            pass  # الرسالة موجودة بالفعل
        else:
            try:
                await query.message.reply_text(
                    helpers.getTextWelcome(update.effective_user.username or ""),
                    reply_markup=helpers.getReplyMarkup(user_id),
                    parse_mode='Markdown'
                )
            except Exception as e2:
                logger.error(f"back_to_main error: {e2}")

    return ConversationHandler.END


# =========================
# CONVERSATION HANDLER (FIXED)
# =========================
def conversationHandler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_deposit, pattern="^deposit$")
        ],

        states={
            # 📌 اختيار المحفظة
            WALLET_SELECT: [
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(wallet_selected, pattern="^[a-z0-9_-]+_deposit$")
            ],

            # 📌 إدخال رقم العملية
            TRANSACTION_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_transaction_id)
            ],

            # 📌 إدخال المبلغ
            AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)
            ],

            # 📌 تأكيد الإيداع
            CONFIRM: [
                CallbackQueryHandler(confirm_deposit, pattern="^(confirm_deposit|cancel_deposit)$")
            ]
        },

        fallbacks=[
            MessageHandler(filters.COMMAND, cancel)
        ],

        allow_reentry=True,
        per_user=True,
        per_chat=True,
        per_message=False,
    )