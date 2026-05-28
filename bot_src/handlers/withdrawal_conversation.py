from telegram.ext import CallbackQueryHandler, ConversationHandler, MessageHandler, filters
import supabase_integration as supa
import Logger
from utils import helpers

logger = Logger.getLogger()

# =========================
# 📌 حالات المحادثة
# =========================
METHOD_SELECT, ACCOUNT_NUMBER, AMOUNT, CONFIRM = range(4)

withdrawal_states = {}


# =========================
# 📌 عرض طرق السحب
# =========================
async def handle_withdrawal(update, context):
    query = update.callback_query
    await query.answer()

    methods = [m for m in supa.get_active_withdrawal_methods() if m.get("key")]

    if not methods:
        await query.edit_message_text("❌ لا توجد طرق سحب متاحة حالياً")
        return ConversationHandler.END

    keyboard = []

    for m in methods:
        keyboard.append([
            {
                "text": f"{m.get('name')}",
                "callback_data": f"{m.get('key')}_withdrawal"
            }
        ])

    # 🔥 زر رجوع
    keyboard.append([
        {
            "text": "🔙 رجوع",
            "callback_data": "back_to_main_withdrawal"
        }
    ])

    try:
        await query.edit_message_text(
            "💸 اختر طريقة السحب:",
            reply_markup={"inline_keyboard": keyboard}
        )
    except Exception as e:
        if "not modified" in str(e).lower():
            pass
        else:
            logger.error(f"handle_withdrawal edit error: {e}")

    return METHOD_SELECT


# =========================
# 📌 اختيار طريقة السحب
# =========================
async def method_selected(update, context):
    query = update.callback_query
    await query.answer()

    key = query.data.rsplit("_withdrawal", 1)[0]
    logger.info(f"method_selected called with key: {key}, full_data: {query.data}")

    method = supa.get_withdrawal_method_by_key(key)

    if not method:
        logger.error(f"Method with key {key} not found. Available methods: {supa.get_active_withdrawal_methods()}")
        await query.edit_message_text(f"❌ طريقة السحب غير موجودة: {key}")
        return ConversationHandler.END

    user_id = update.effective_user.id
    logger.info(f"User {user_id} selected method: {method.get('name')}")

    withdrawal_states[user_id] = {
        "method": method,
        "step": "account_number"
    }

    name = method.get('name')
    input_label = method.get('input_label', 'أدخل رقم الحساب')

    msg = f"""💸 طريقة السحب: **{name}**

✏️ {input_label}:
"""

    try:
        await query.edit_message_text(msg, parse_mode="Markdown")
        logger.info(f"Sent account number request to user {user_id}")
    except Exception as e:
        logger.error(f"method_selected error for user {user_id}: {e}")
        await query.message.reply_text(msg, parse_mode="Markdown")

    logger.info(f"Returning ACCOUNT_NUMBER ({ACCOUNT_NUMBER}) for user {user_id}")
    return ACCOUNT_NUMBER


# =========================
# 📌 الحصول على رقم الحساب
# =========================
async def get_account_number(update, context):
    try:
        user_id = update.effective_user.id
        logger.info(f"========== get_account_number ENTRY for user {user_id} ==========")
        logger.info(f"Update type: {type(update)}, has message: {hasattr(update, 'message')}")

        if user_id not in withdrawal_states:
            logger.warning(f"User {user_id} not in withdrawal_states. States: {withdrawal_states}")
            await update.message.reply_text("❌ انتهت الجلسة. ابدأ من جديد.")
            return ConversationHandler.END

        logger.info(f"User {user_id} found in states: {withdrawal_states[user_id]}")

        account_number = update.message.text.strip()
        logger.info(f"User {user_id} entered account_number: {account_number}")

        if not account_number:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
            return ACCOUNT_NUMBER

        withdrawal_states[user_id]["account_number"] = account_number
        withdrawal_states[user_id]["step"] = "amount"
        logger.info(f"Updated state for user {user_id}: {withdrawal_states[user_id]}")

        try:
            await update.message.reply_text(
                "💰 الآن أدخل **المبلغ** المراد سحبه:",
                parse_mode="Markdown"
            )
            logger.info(f"✅ SUCCESS: Sent amount request to user {user_id}")
        except Exception as e:
            logger.error(f"❌ ERROR sending amount request to user {user_id}: {e}")
            # Fallback without markdown
            try:
                await update.message.reply_text("💰 الآن أدخل المبلغ المراد سحبه:")
                logger.info(f"✅ SUCCESS (fallback): Sent amount request to user {user_id}")
            except Exception as e2:
                logger.error(f"❌ COMPLETE FAILURE: {e2}")

        logger.info(f"========== get_account_number RETURNING AMOUNT ({AMOUNT}) for user {user_id} ==========")
        return AMOUNT
    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR in get_account_number: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ConversationHandler.END


# =========================
# 📌 الحصول على المبلغ
# =========================
async def get_amount(update, context):
    user_id = update.effective_user.id
    logger.info(f"========== get_amount START for user {user_id} ==========")

    try:
        if user_id not in withdrawal_states:
            logger.warning(f"User {user_id} not in withdrawal_states in get_amount")
            await update.message.reply_text("❌ انتهت الجلسة. ابدأ من جديد.")
            return ConversationHandler.END

        logger.info(f"User {user_id} state: {withdrawal_states[user_id]}")

        try:
            amount = float(update.message.text.replace(",", "").strip())
            logger.info(f"User {user_id} entered amount: {amount}")
        except ValueError:
            logger.warning(f"User {user_id} entered invalid amount: {update.message.text}")
            await update.message.reply_text("❌ يرجى إدخال مبلغ صحيح (أرقام فقط)")
            return AMOUNT

        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر")
            return AMOUNT

        # الحد الأدنى للسحب
        MIN_WITHDRAWAL = 100000
        if amount < MIN_WITHDRAWAL:
            await update.message.reply_text(
                f"❌ الحد الأدنى للسحب هو {MIN_WITHDRAWAL:,.0f} ل.س\n"
                f"💰 المبلغ المدخل: {amount:,.0f} ل.س\n\n"
                f"يرجى إدخال مبلغ أكبر أو يساوي {MIN_WITHDRAWAL:,.0f} ل.س"
            )
            return AMOUNT

        # حساب نسبة الخصم
        try:
            fee_percentage = supa.get_withdrawal_fee_percentage()
        except Exception as e:
            logger.error(f"Error getting fee percentage: {e}")
            fee_percentage = 5.0  # default

        fee_amount = amount * (fee_percentage / 100)
        net_amount = amount - fee_amount

        withdrawal_states[user_id]["amount"] = amount
        withdrawal_states[user_id]["fee_amount"] = fee_amount
        withdrawal_states[user_id]["net_amount"] = net_amount
        withdrawal_states[user_id]["step"] = "confirm"

        method = withdrawal_states[user_id]["method"]
        account_number = withdrawal_states[user_id]["account_number"]

        logger.info(f"Preparing confirmation for user {user_id}: method={method}, account={account_number}")

        # عرض رسالة التأكيد
        method_name = method.get('name') if method else 'غير معروف'

        confirm_msg = (
            f"📋 تأكيد عملية السحب\n\n"
            f"💸 طريقة السحب: {method_name}\n"
            f"🔢 العنوان: `{account_number}`\n"
            f"💰 المبلغ: {amount:,.0f} ل.س\n"
            f"📊 نسبة الخصم: {fee_percentage}%\n"
            f"💸 قيمة الخصم: {fee_amount:,.0f} ل.س\n"
            f"✅ المبلغ الصافي: {net_amount:,.0f} ل.س\n\n"
            f"هل تؤكد عملية السحب؟"
        )

        logger.info(f"Confirmation message prepared for user {user_id}")

        # إنشاء الكيبورد بشكل صحيح
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ تأكيد", callback_data="confirm_withdrawal"),
                InlineKeyboardButton("❌ إلغاء", callback_data="cancel_withdrawal")
            ]
        ])

        logger.info(f"Sending confirmation message to user {user_id}...")

        try:
            await update.message.reply_text(
                confirm_msg,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            logger.info(f"✅ SUCCESS: Sent confirmation message to user {user_id}")
        except Exception as e:
            logger.error(f"❌ ERROR sending confirmation to user {user_id}: {e}")
            # Try without markdown
            try:
                await update.message.reply_text(
                    confirm_msg,
                    reply_markup=keyboard
                )
                logger.info(f"✅ SUCCESS (no markdown): Sent confirmation to user {user_id}")
            except Exception as e2:
                logger.error(f"❌ ERROR (no markdown): {e2}")
                # Final fallback - send without keyboard
                try:
                    await update.message.reply_text(confirm_msg)
                    logger.info(f"✅ SUCCESS (no keyboard): Sent confirmation to user {user_id}")
                except Exception as e3:
                    logger.error(f"❌ COMPLETE FAILURE: {e3}")

        logger.info(f"========== get_amount END for user {user_id} - returning CONFIRM ==========")
        return CONFIRM

    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR in get_amount for user {user_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END


# =========================
# 📌 تأكيد/إلغاء السحب
# =========================
async def confirm_withdrawal(update, context):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    logger.info(f"confirm_withdrawal called by user {user_id}, data={data}")

    if user_id not in withdrawal_states:
        logger.warning(f"User {user_id} not in withdrawal_states in confirm")
        await query.edit_message_text("❌ انتهت الجلسة. ابدأ من جديد.")
        return ConversationHandler.END

    state = withdrawal_states[user_id]
    method = state["method"]
    amount = state["amount"]
    account_number = state["account_number"]
    fee_amount = state.get("fee_amount", 0)
    net_amount = state.get("net_amount", amount)

    if data == "cancel_withdrawal":
        del withdrawal_states[user_id]
        await query.edit_message_text("❌ تم إلغاء السحب.")
        return ConversationHandler.END

    # التحقق من الرصيد
    user_balance = supa.get_user_balance(user_id)
    if user_balance < amount:
        del withdrawal_states[user_id]
        await query.edit_message_text(
            f"❌ رصيدك غير كافي!\n\n"
            f"💰 رصيدك: {user_balance:,.0f} ل.س\n"
            f"💸 المطلوب: {amount:,.0f} ل.س"
        )
        return ConversationHandler.END

    # تأكيد السحب
    logger.info(f"About to insert withdrawal for user {user_id}: amount={amount}, method={method}")
    try:
        method_key = method.get("key") or method.get("name")
        logger.info(f"Using method_key: {method_key}")
        
        result = supa.insert_withdrawal(
            telegram_id=user_id,
            username=update.effective_user.username or str(user_id),
            amount_syp=amount,
            account_number=account_number,
            method_key=method_key,
            fee_amount=fee_amount
        )
        logger.info(f"Withdrawal insert result: {result}")

        del withdrawal_states[user_id]

        await query.edit_message_text(
            f"✅ تم إرسال طلب السحب\n\n"
            f"💸 {method.get('name')}\n"
            f"🔢 العنوان: `{account_number}`\n"
            f"💰 المبلغ: {amount:,.0f} ل.س\n"
            f"📊 نسبة الخصم: {supa.get_withdrawal_fee_percentage()}%\n"
            f"💸 الخصم: {fee_amount:,.0f} ل.س\n"
            f"✅ الصافي: {net_amount:,.0f} ل.س\n"
            f"📋 رقم الطلب: {result}\n\n"
            f"⏳ في انتظار الموافقة..."
        )
    except Exception as e:
        logger.error(f"insert_withdrawal failed: {e}")
        await query.edit_message_text(f"❌ خطأ في حفظ السحب: {e}")

    return ConversationHandler.END


# =========================
# 🔙 رجوع للقائمة الرئيسية
# =========================
async def back_to_main_withdrawal(update, context):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    withdrawal_states.pop(user_id, None)

    try:
        await query.edit_message_text(
            helpers.getTextWelcome(update.effective_user.username or ""),
            reply_markup=helpers.getReplyMarkup(user_id),
            parse_mode='Markdown'
        )
    except Exception as e:
        if "not modified" in str(e).lower():
            pass
        else:
            try:
                await query.message.reply_text(
                    helpers.getTextWelcome(update.effective_user.username or ""),
                    reply_markup=helpers.getReplyMarkup(user_id),
                    parse_mode='Markdown'
                )
            except Exception as e2:
                logger.error(f"back_to_main_withdrawal error: {e2}")

    return ConversationHandler.END


# =========================
# ❌ إلغاء
# =========================
async def cancel(update, context):
    withdrawal_states.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ تم الإلغاء")
    return ConversationHandler.END


# =========================
# 🔥 CONVERSATION HANDLER
# =========================
def conversationHandler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_withdrawal, pattern="^withdrawal$")
        ],

        states={
            METHOD_SELECT: [
                CallbackQueryHandler(back_to_main_withdrawal, pattern="^back_to_main_withdrawal$"),
                CallbackQueryHandler(method_selected, pattern="^[a-z0-9_-]+_withdrawal$")
            ],
            ACCOUNT_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_account_number)
            ],
            AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_withdrawal, pattern="^(confirm_withdrawal|cancel_withdrawal)$")
            ]
        },

        fallbacks=[
            MessageHandler(filters.COMMAND, cancel)
        ],

        allow_reentry=True,
        per_user=True
    )
