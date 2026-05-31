"""
Advanced iChancy Operations Handler
يعالج: شحن، سحب، معلومات الحساب، عمليات، وغيرها

ملاحظة مهمة:
- شحن رصيد iChancy = إيداع في حساب اللاعب في الموقع + خصم من رصيد البوت
- سحب رصيد iChancy = سحب من حساب اللاعب في الموقع + إضافة إلى رصيد البوت
- شحن كامل الرصيد = سحب كامل رصيد اللاعب من الموقع + إضافة إلى رصيد البوت
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.iChancyAPI import iChancyAPI
import store
import supabase_integration as supa
import Logger
import handlers.ichancy

logger = Logger.getLogger()

# =============================
# 📊 معلومات الحساب (Account Info)
# =============================

async def ichancy_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات الحساب بشكل قابل للنسخ"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        # جلب بيانات الحساب من Supabase
        result = supa.get_client().table("users_ichancy_details") \
            .select("*") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            await query.edit_message_text("❌ لم يتم العثور على حساب")
            return
        
        account = result.data[0]
        username = account.get("username", "N/A")
        password = account.get("password", "N/A")
        email = account.get("email", "N/A")
        player_id = account.get("player_id", "N/A")
        
        # جلب الرصيد من API
        api = handlers.ichancy.get_api()
        site_balance = "غير متاح"
        if api:
            balance_result = api.get_player_balance_by_username(username)
            if balance_result.get('success'):
                site_balance = balance_result.get('balance', 0)
        
        # جلب رصيد البوت
        bot_balance = store.get_user_balance(user_id)
        
        # رسالة قابلة للنسخ
        message = (
            f"📋 <b>معلومات الحساب</b>\n\n"
            f"👤 <b>اسم المستخدم:</b>\n<code>{username}</code>\n\n"
            f"🔐 <b>كلمة المرور:</b>\n<code>{password}</code>\n\n"
            f"📧 <b>البريد الإلكتروني:</b>\n<code>{email}</code>\n\n"
            f"🆔 <b>معرف اللاعب:</b>\n<code>{player_id}</code>\n\n"
            f"💰 <b>رصيد الموقع:</b>\n<code>{site_balance}</code>\n\n"
            f"💳 <b>رصيد البوت:</b>\n<code>{bot_balance}</code>"
        )
        
        keyboard = [[
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_ichancy")
        ]]
        
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in ichancy_account_info: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")


# =============================
# 💰 شحن رصيد الموقع (خصم من رصيد البوت)
# =============================

async def ichancy_deposit_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شحن رصيد الموقع - يخصم المبلغ من رصيد البوت ويودعه في حساب اللاعب في الموقع"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await query.edit_message_text("❌ لم يتم العثور على حساب")
            return
        
        # عرض رصيد البوت الحالي
        bot_balance = store.get_user_balance(user_id)
        
        context.user_data['ichancy_deposit'] = True
        
        await query.edit_message_text(
            f"💰 <b>شحن رصيد الموقع</b>\n\n"
            f"💳 رصيد البوت الحالي: <code>{bot_balance}</code>\n\n"
            f"أدخل مبلغ الشحن (سيتم خصمه من رصيد البوت وإضافته لرصيد الموقع):",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ إلغاء", callback_data="back_to_ichancy")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error in ichancy_deposit_advanced: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")


async def handle_ichancy_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مبلغ الشحن - خصم من رصيد البوت وإيداع في الموقع"""
    user_id = str(update.effective_user.id)
    
    try:
        amount = float(update.message.text)
        
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من 0")
            return
        
        # التحقق من رصيد البوت قبل العملية
        bot_balance = store.get_user_balance(user_id)
        if bot_balance < amount:
            await update.message.reply_text(
                f"❌ رصيد البوت غير كافي!\n\n"
                f"💳 رصيد البوت: <code>{bot_balance}</code>\n"
                f"💰 المبلغ المطلوب: <code>{amount}</code>",
                parse_mode="HTML"
            )
            context.user_data.pop('ichancy_deposit', None)
            return
        
        # جلب بيانات الحساب
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await update.message.reply_text("❌ لم يتم العثور على حساب")
            return
        
        account = result.data[0]
        player_id = account.get("player_id")
        
        # تنفيذ عملية الشحن في الموقع
        api = handlers.ichancy.get_api()
        if not api:
            await update.message.reply_text("❌ لا يمكن الاتصال بخوادم iChancy حالياً")
            return
        deposit_result = api.deposit_to_player(player_id, amount, "Telegram Bot Deposit")
        
        if deposit_result.get('success'):
            new_site_balance = deposit_result.get('new_balance', 0)
            
            # خصم المبلغ من رصيد البوت
            new_bot_balance = bot_balance - amount
            store.update_user_balance(user_id, new_bot_balance)
            
            message = (
                f"✅ <b>تم الشحن بنجاح!</b>\n\n"
                f"💰 <b>المبلغ المشحن:</b> <code>{amount}</code>\n"
                f"🌐 <b>رصيد الموقع الجديد:</b> <code>{new_site_balance}</code>\n"
                f"💳 <b>رصيد البوت الجديد:</b> <code>{new_bot_balance}</code>"
            )
            
            # حفظ العملية
            try:
                supa.get_client().table("transactions_ichancy").insert({
                    "telegram_id": user_id,
                    "type": "deposit_to_site",
                    "amount": amount,
                    "new_balance": new_site_balance,
                    "status": "completed"
                }).execute()
            except:
                pass
            
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            error_msg = deposit_result.get('error', 'Unknown error')
            await update.message.reply_text(f"❌ فشل الشحن: {error_msg}")
        
        context.user_data.pop('ichancy_deposit', None)
        
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
    except Exception as e:
        logger.error(f"Error in handle_ichancy_deposit_amount: {e}")
        await update.message.reply_text(f"❌ خطأ: {str(e)}")


# =============================
# 💸 سحب رصيد الموقع (إضافة إلى رصيد البوت)
# =============================

async def ichancy_withdraw_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سحب رصيد الموقع - يسحب من حساب اللاعب في الموقع ويضيفه إلى رصيد البوت"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await query.edit_message_text("❌ لم يتم العثور على حساب")
            return
        
        account = result.data[0]
        username = account.get("username")
        
        # جلب رصيد الموقع الحالي
        site_balance = "غير متاح"
        api = handlers.ichancy.get_api()
        if api:
            balance_result = api.get_player_balance_by_username(username)
            if balance_result.get('success'):
                site_balance = balance_result.get('balance', 0)
        
        context.user_data['ichancy_withdraw'] = True
        
        await query.edit_message_text(
            f"💸 <b>سحب رصيد الموقع</b>\n\n"
            f"🌐 رصيد الموقع الحالي: <code>{site_balance}</code>\n\n"
            f"أدخل مبلغ السحب (سيتم سحبه من رصيد الموقع وإضافته لرصيد البوت):",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ إلغاء", callback_data="back_to_ichancy")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error in ichancy_withdraw_advanced: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")


async def handle_ichancy_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مبلغ السحب - سحب من الموقع وإضافة لرصيد البوت"""
    user_id = str(update.effective_user.id)
    
    try:
        amount = float(update.message.text)
        
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من 0")
            return
        
        # جلب بيانات الحساب
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await update.message.reply_text("❌ لم يتم العثور على حساب")
            return
        
        account = result.data[0]
        player_id = account.get("player_id")
        
        # التحقق من رصيد الموقع قبل العملية
        api = handlers.ichancy.get_api()
        if not api:
            await update.message.reply_text("❌ لا يمكن الاتصال بخوادم iChancy حالياً")
            return
        
        balance_check = api.get_player_balance_by_id(player_id)
        if balance_check.get('success'):
            site_balance = balance_check.get('balance', 0)
            if site_balance < amount:
                await update.message.reply_text(
                    f"❌ رصيد الموقع غير كافي!\n\n"
                    f"🌐 رصيد الموقع: <code>{site_balance}</code>\n"
                    f"💰 المبلغ المطلوب: <code>{amount}</code>",
                    parse_mode="HTML"
                )
                context.user_data.pop('ichancy_withdraw', None)
                return
        
        # تنفيذ عملية السحب من الموقع
        withdraw_result = api.withdraw_from_player(player_id, amount, "Telegram Bot Withdraw")
        
        if withdraw_result.get('success'):
            new_site_balance = withdraw_result.get('new_balance', 0)
            
            # إضافة المبلغ إلى رصيد البوت
            bot_balance = store.get_user_balance(user_id)
            new_bot_balance = bot_balance + amount
            store.update_user_balance(user_id, new_bot_balance)
            
            message = (
                f"✅ <b>تم السحب بنجاح!</b>\n\n"
                f"💸 <b>المبلغ المسحوب:</b> <code>{amount}</code>\n"
                f"🌐 <b>رصيد الموقع الجديد:</b> <code>{new_site_balance}</code>\n"
                f"💳 <b>رصيد البوت الجديد:</b> <code>{new_bot_balance}</code>"
            )
            
            # حفظ العملية
            try:
                supa.get_client().table("transactions_ichancy").insert({
                    "telegram_id": user_id,
                    "type": "withdraw_from_site",
                    "amount": amount,
                    "new_balance": new_site_balance,
                    "status": "completed"
                }).execute()
            except:
                pass
            
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            error_msg = withdraw_result.get('error', 'Unknown error')
            await update.message.reply_text(f"❌ فشل السحب: {error_msg}")
        
        context.user_data.pop('ichancy_withdraw', None)
        
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
    except Exception as e:
        logger.error(f"Error in handle_ichancy_withdraw_amount: {e}")
        await update.message.reply_text(f"❌ خطأ: {str(e)}")


async def handle_ichancy_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text input for advanced iChancy deposit/withdraw workflows."""
    if context.user_data.get('ichancy_deposit'):
        await handle_ichancy_deposit_amount(update, context)
        return

    if context.user_data.get('ichancy_withdraw'):
        await handle_ichancy_withdraw_amount(update, context)
        return


# =============================
# 📈 عمليات (Transactions)
# =============================

async def ichancy_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض آخر العمليات"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        # جلب آخر 10 عمليات
        result = supa.get_client().table("transactions_ichancy") \
            .select("*") \
            .eq("telegram_id", user_id) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        
        transactions = result.data if result.data else []
        
        if not transactions:
            message = "📊 <b>لا توجد عمليات</b>"
        else:
            message = "📊 <b>آخر العمليات:</b>\n\n"
            for tx in transactions:
                tx_type_map = {
                    "deposit_to_site": "💰 شحن موقع",
                    "withdraw_from_site": "💸 سحب موقع",
                    "deposit": "💰 شحن",
                    "withdraw": "💸 سحب",
                    "transfer_all": "⚡ شحن كامل"
                }
                tx_type = tx_type_map.get(tx.get("type", ""), tx.get("type", "عملية"))
                amount = tx.get("amount", 0)
                balance = tx.get("new_balance", 0)
                
                message += (
                    f"{tx_type}\n"
                    f"المبلغ: <code>{amount}</code>\n"
                    f"الرصيد: <code>{balance}</code>\n"
                    f"─────────────────\n"
                )
        
        keyboard = [[
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_ichancy")
        ]]
        
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in ichancy_transactions: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")


# =============================
# ⚡ شحن كامل الرصيد (سحب كامل رصيد الموقع إلى رصيد البوت)
# =============================

async def ichancy_deposit_all_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شحن كامل الرصيد - سحب كامل رصيد اللاعب من الموقع وإضافته إلى رصيد البوت"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        # جلب بيانات الحساب
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await query.edit_message_text("❌ لم يتم العثور على حساب")
            return
        
        account = result.data[0]
        player_id = account.get("player_id")
        
        # جلب الرصيد الحالي من الموقع
        api = handlers.ichancy.get_api()
        if not api:
            await query.edit_message_text("❌ لا يمكن الاتصال بخوادم iChancy حالياً")
            return
        balance_result = api.get_player_balance_by_id(player_id)
        
        if not balance_result.get('success'):
            await query.edit_message_text("❌ لا يمكن جلب الرصيد")
            return
        
        current_balance = balance_result.get('balance', 0)
        
        if current_balance <= 0:
            await query.edit_message_text("❌ لا يوجد رصيد في الموقع للشحن")
            return
        
        # سحب كامل الرصيد من الموقع
        withdraw_result = api.withdraw_from_player(
            player_id, 
            current_balance, 
            "Telegram Bot - Transfer All to Bot Balance"
        )
        
        if withdraw_result.get('success'):
            # إضافة الرصيد المسحوب إلى رصيد البوت
            bot_balance = store.get_user_balance(user_id)
            new_bot_balance = bot_balance + current_balance
            store.update_user_balance(user_id, new_bot_balance)
            
            message = (
                f"✅ <b>تم شحن كامل الرصيد!</b>\n\n"
                f"💰 <b>المبلغ المشحون:</b> <code>{current_balance}</code>\n"
                f"🌐 <b>رصيد الموقع:</b> <code>0</code>\n"
                f"💳 <b>رصيد البوت الجديد:</b> <code>{new_bot_balance}</code>"
            )
            
            # حفظ العملية
            try:
                supa.get_client().table("transactions_ichancy").insert({
                    "telegram_id": user_id,
                    "type": "transfer_all",
                    "amount": current_balance,
                    "new_balance": 0,
                    "status": "completed"
                }).execute()
            except:
                pass
            
            await query.edit_message_text(message, parse_mode="HTML")
        else:
            await query.edit_message_text(f"❌ فشل العملية: {withdraw_result.get('error', 'Unknown')}")
            
    except Exception as e:
        logger.error(f"Error in ichancy_deposit_all_advanced: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")
