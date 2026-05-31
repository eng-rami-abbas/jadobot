from telegram.ext import filters, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, CommandHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from services.iChancyAPI import iChancyAPI
import random, string, asyncio
from datetime import datetime
import handlers.ichancy
import supabase_integration as supa
import Logger

logger = Logger.getLogger()

NAME, PASSWORD = range(2)


def generateRandomString(length=5):
    return ''.join(random.choices(string.ascii_letters, k=length))


def get_api():
    """Get a shared iChancyAPI instance."""
    try:
        return iChancyAPI.get_shared() or iChancyAPI()
    except Exception as e:
        logger.error(f"Failed to create iChancyAPI instance: {e}")
        return None


async def button_create_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    account = supa.get_ichancy_details_by_telegram_id(telegram_id)

    if account and account.get('username'):
        await update.callback_query.answer("لديك حساب مسجل مسبقا", show_alert=True)
        return ConversationHandler.END

    await update.callback_query.edit_message_text("ادخل اسم حساب الـ Ichancy الجديد")
    return NAME


USERNAME_SUFFIX = '_jado2026'

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()

    if len(name) < 3:
        await update.message.reply_text("الاسم يجب أن يكون على الأقل 3 أحرف")
        return NAME

    # تنظيف الاسم وإضافة اللاحقة
    base_name_clean = ''.join(c if c.isalnum() else '' for c in name.lower())
    if not base_name_clean:
        await update.message.reply_text("الاسم يجب أن يحتوي على أحرف أو أرقام صالحة")
        return NAME

    # إضافة اللاحقة _jado2026 لاسم المستخدم
    full_username = base_name_clean + USERNAME_SUFFIX
    context.user_data['name'] = full_username
    context.user_data['display_name'] = name  # الاسم الأصلي للعرض

    # رسالة واحدة فقط تطلب كلمة المرور
    await update.message.reply_text(
        f"✅ اسم المستخدم الخاص بك سيكون: <code>{full_username}</code>\n\n"
        f"🔑 أدخل كلمة مرور (8 أحرف على الأقل):",
        parse_mode='HTML'
    )
    return PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text

    if len(password) < 8:
        await update.message.reply_text("كلمة السر يجب أن تكون 8 أحرف على الأقل")
        return PASSWORD

    context.user_data['password'] = password

    # توليد email فريد
    random_suffix = generateRandomString(6).lower()
    base_name = context.user_data['name'].lower()
    base_name_clean = ''.join(c if c.isalnum() else '' for c in base_name)
    email = f"{base_name_clean}_{random_suffix}@jadobot.jado"

    context.user_data['email'] = email

    await update.message.reply_text("جاري إنشاء الحساب... ⏳")

    # Call the handler directly - ensures errors are properly handled and Supabase save is verified
    await handle_create_account(update, context)

    return ConversationHandler.END


async def handle_create_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إنشاء الحساب - يتم استدعاؤها مباشرة وليس كـ fire-and-forget"""
    telegram_user_id = str(update.effective_user.id)
    name = context.user_data.get('name')
    password = context.user_data.get('password')
    email = context.user_data.get('email')
    display_name = context.user_data.get('display_name', name)

    logger.info(f"Creating account for user {telegram_user_id}: {name} (display: {display_name})")

    # Use shared API instance
    api = get_api()
    if not api:
        await update.message.reply_text(
            "❌ لا يمكن الاتصال بخوادم iChancy حالياً\n\n"
            "يرجى المحاولة لاحقاً أو التواصل مع الدعم: @jadobotichancy"
        )
        return

    # REGISTER ACCOUNT (async) - ONLY ONCE
    try:
        result = await api.register_player(
            username=name,
            password=password,
            email=email,
            parent_id=handlers.ichancy.PARENT_ID
        )
    except Exception as e:
        logger.error(f"Register player exception: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ حدث خطأ أثناء إنشاء الحساب:\n{str(e)}\n\n"
            "يرجى المحاولة لاحقاً أو التواصل مع الدعم: @jadobotichancy"
        )
        return

    logger.info(f"Register result: {result}")

    # VERIFY USER - get player ID (async)
    player_id = None
    if result.get('success'):
        player_id = result.get('player_id')
        if not player_id:
            for i in range(3):
                try:
                    player_id = await api.get_player_id_by_username(name)
                    logger.info(f"Verification attempt {i+1}: player_id={player_id}")
                except Exception as e:
                    logger.error(f"VERIFY ERROR (attempt {i+1}): {e}")
                    player_id = None

                if player_id:
                    break
                await asyncio.sleep(2)

    logger.info(f"VERIFY RESULT: player_id={player_id}")

    # SUCCESS CHECK
    if result.get('success'):
        # DATABASE - Save user data
        try:
            supa.upsert_user(
                telegram_id=int(telegram_user_id),
                username=update.effective_user.username or "",
                first_name=update.effective_user.first_name or "",
                last_name=update.effective_user.last_name or ""
            )
            logger.info(f"Upserted user meta to Supabase for user {telegram_user_id}")
        except Exception as e:
            logger.warning(f"Could not upsert user meta to Supabase: {e}")

        # Save ichancy details - CRITICAL STEP
        save_success = False
        try:
            save_result = supa.upsert_ichancy_details(
                telegram_id=telegram_user_id,
                username=name,
                email=email,
                password=password,
                player_id=str(player_id) if player_id else "0"
            )
            # Verify the save worked
            if save_result:
                logger.info(f"Supabase upsert_ichancy_details saved successfully for user {telegram_user_id}")
                save_success = True
            else:
                logger.error(f"upsert_ichancy_details returned None for user {telegram_user_id}")
        except Exception as e:
            logger.error(f"CRITICAL: Could not save ichancy details to Supabase: {e}", exc_info=True)

        # Double-check: Verify the data was actually saved
        if save_success:
            try:
                verify_account = supa.get_ichancy_details_by_telegram_id(telegram_user_id)
                if verify_account and verify_account.get('username'):
                    logger.info(f"Verified ichancy details saved for user {telegram_user_id}: username={verify_account.get('username')}")
                else:
                    logger.error(f"VERIFICATION FAILED: ichancy details not found after save for user {telegram_user_id}")
                    save_success = False
            except Exception as e:
                logger.error(f"Could not verify ichancy details save: {e}")

        # MESSAGE SUCCESS
        success_message = (
            f"✅ تم إنشاء الحساب بنجاح!\n\n"
            f"👤 الحساب: <code>{name}</code>\n"
            f"🔒 كلمة السر: <code>{password}</code>\n"
            f"📧 الإيميل: <code>{email}</code>\n"
            f"🆔 رقم اللاعب: {player_id if player_id else 'قيد المعالجة'}\n\n"
            f"🔗 رابط الدخول: https://www.ichancy.com/ar\n\n"
            f"⚠️ احفظ بيانات حسابك في مكان آمن!"
        )

        await update.message.reply_text(success_message, parse_mode='HTML')

        # Show iChancy keyboard with account buttons (charge, withdraw, etc.)
        from handlers.ichancy import get_ichancy_keyboard
        await update.message.reply_text(
            "🎮 القائمة:",
            reply_markup=get_ichancy_keyboard(int(telegram_user_id))
        )

    else:
        error_msg = result.get('error', 'Unknown error')

        if 'Authentication failed' in error_msg or 'Cloudflare' in error_msg:
            user_error = (
                "❌ خطأ في الاتصال بخوادم ichancy\n\n"
                "السبب المحتمل:\n"
                "• حماية Cloudflare تحظر الاتصال من الخادم\n"
                "• مشكلة مؤقتة في الخوادم\n\n"
                "الحل:\n"
                "حاول مرة أخرى بعد قليل أو تواصل مع الإدارة: @jadobotichancy"
            )
        elif 'Duplicate login' in error_msg or 'duplicate' in error_msg.lower() or 'مستخدم' in error_msg:
            user_error = "❌ اسم المستخدم مستخدم بالفعل! الرجاء اختيار اسم آخر."
        elif 'email' in error_msg.lower() or 'بريد' in error_msg:
            user_error = f"❌ خطأ في البريد الإلكتروني: {error_msg}\n\nحاول مرة أخرى."
        elif 'password' in error_msg.lower() or 'كلمة' in error_msg:
            user_error = f"❌ خطأ في كلمة السر: {error_msg}\n\nيجب أن تكون على الأقل 8 أحرف."
        elif 'parent' in error_msg.lower():
            user_error = "❌ خطأ في نظام الإحالة. تواصل مع الدعم."
        else:
            user_error = f"❌ خطأ:\n{error_msg}"

        await update.message.reply_text(user_error)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        'تم إلغاء إنشاء الحساب',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_create_account_handler, pattern='^ichancy_create_account$')],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False,
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )
    return conv_handler
