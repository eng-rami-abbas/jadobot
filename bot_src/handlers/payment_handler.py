"""
معالج المدفوعات والمعاملات المالية
"""

import logging
import random
import string
from datetime import datetime
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

import store
import config.telegram
import handlers.ichancy
from utils import helpers
import handlers.referral_system

logger = logging.getLogger(__name__)

class PaymentHandler:
    """معالج المدفوعات"""
    
    # إعدادات طرق الدفع
    PAYMENT_METHODS = {
        "syriatel_cash": {
            "name": "Syriatel Cash",
            "emoji": "📱",
            "min_amount": 25000,
            "max_amount": 10000000,
            "instructions": "يرجى التحويل إلى أحد الأرقام التالية:\n• 0991005298\n• 0980375513",
            "input_prompt": "رقم عملية التحويل"
        },
        "my_method": {
           "name": "My Payment",
           "emoji": "💳",
           "min_amount": 1000,
           "max_amount": 1000000,
           "instructions": "أدخل رقم العملية أولاً",
           "input_prompt": "📌 أدخل المبلغ:",
           "steps": ["transaction_id", "amount"]  # 🔥 مهم
        },
        "bemo": {
            "name": "Bemo",
            "emoji": "🏦",
            "min_amount": 10000,
            "max_amount": 5000000,
            "instructions": "تحويل بنكي إلى حساب Bemo\nرقم الحساب: 123456789",
            "input_prompt": "رقم عملية التحويل البنكي"
        },
        "payeer": {
            "name": "Payeer",
            "emoji": "💳",
            "min_amount": 1000,
            "max_amount": 1000000,
            "instructions": "تحويل إلى محفظة Payeer\nالحساب: P123456789",
            "input_prompt": "رقم حساب Payeer"
        },
        "crypto": {
            "name": "USDT",
            "emoji": "💰",
            "min_amount": 10000,
            "max_amount": 5000000,
            "instructions": "تحويل USDT عبر شبكة TRC20\nالعنوان: TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "input_prompt": "رقم المعاملة (Transaction Hash)"
        }
    }
    
    @staticmethod
    def format_currency(amount: int) -> str:
        """تنسيق العملة"""
        return f"{amount:,}"
    
    @staticmethod
    def validate_amount(amount_str: str, min_amount: int = 0, max_amount: int = 1000000000) -> tuple:
        """التحقق من صحة المبلغ"""
        try:
            amount = int(amount_str)
            
            if amount <= 0:
                return False, 0, "❌ المبلغ يجب أن يكون أكبر من صفر"
            
            if amount < min_amount:
                return False, 0, f"❌ الحد الأدنى هو {PaymentHandler.format_currency(min_amount)}"
            
            if amount > max_amount:
                return False, 0, f"❌ الحد الأقصى هو {PaymentHandler.format_currency(max_amount)}"
            
            return True, amount, ""
            
        except ValueError:
            return False, 0, "❌ يرجى إدخال مبلغ صحيح"
    
    @staticmethod
    async def show_payment_methods(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_type: str = "deposit"):
        """عرض طرق الدفع"""
        user_id = str(update.effective_user.id)
        
        title = "💰 طرق الإيداع" if transaction_type == "deposit" else "💸 طرق السحب"
        
        keyboard = []
        
        # طرق الدفع الأساسية
        basic_methods = ["syriatel_cash", "bemo", "payeer", "crypto"]
        
        for method_id in basic_methods:
            method_info = PaymentHandler.PAYMENT_METHODS[method_id]
            button_text = f"{method_info['emoji']} {method_info['name']}"
            
            if transaction_type == "deposit":
                callback_data = f"deposit_{method_id}"
            else:
                callback_data = f"withdraw_{method_id}"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""
{title}

اختر طريقة الدفع المناسبة:
        """
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
    
    @staticmethod
    async def process_deposit_request(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
        """معالجة طلب الإيداع"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        user = store.getUserByTelegramId(user_id)
        
        if not user:
            await query.edit_message_text("❌ لم يتم العثور على حسابك")
            return
        
        method_info = PaymentHandler.PAYMENT_METHODS.get(method)
        if not method_info:
            await query.edit_message_text("❌ طريقة دفع غير صالحة")
            return
        
        # حفظ البيانات في context
        context.user_data['payment_method'] = method
        context.user_data['transaction_type'] = 'deposit'
        context.user_data['method_info'] = method_info
        
        await query.edit_message_text(
            f"💰 **{method_info['name']} {method_info['emoji']}**\n\n"
            f"أدخل المبلغ المراد إيداعه:\n"
            f"الحد الأدنى: {PaymentHandler.format_currency(method_info['min_amount'])}\n"
            f"الحد الأقصى: {PaymentHandler.format_currency(method_info['max_amount'])}",
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def process_withdraw_request(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
        """معالجة طلب السحب"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        user = store.getUserByTelegramId(user_id)
        
        if not user:
            await query.edit_message_text("❌ لم يتم العثور على حسابك")
            return
        
        method_info = PaymentHandler.PAYMENT_METHODS.get(method)
        if not method_info:
            await query.edit_message_text("❌ طريقة دفع غير صالحة")
            return
        
        # التحقق من الرصيد
        user_balance = user.get('balance', 0)
        
        if user_balance < method_info['min_amount']:
            await query.edit_message_text(
                f"❌ **رصيدك غير كافي للسحب**\n\n"
                f"💵 رصيدك الحالي: {PaymentHandler.format_currency(user_balance)}\n"
                f"الحد الأدنى للسحب: {PaymentHandler.format_currency(method_info['min_amount'])}",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 شحن الرصيد", callback_data='deposit')],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')]
                ])
            )
            return
        
        # حفظ البيانات في context
        context.user_data['payment_method'] = method
        context.user_data['transaction_type'] = 'withdraw'
        context.user_data['method_info'] = method_info
        context.user_data['user_balance'] = user_balance
        
        max_withdraw = min(method_info['max_amount'], user_balance)
        
        await query.edit_message_text(
            f"💸 **{method_info['name']} {method_info['emoji']}**\n\n"
            f"أدخل المبلغ المراد سحبه:\n"
            f"الحد الأدنى: {PaymentHandler.format_currency(method_info['min_amount'])}\n"
            f"الحد الأقصى: {PaymentHandler.format_currency(max_withdraw)}\n"
            f"💵 رصيدك الحالي: {PaymentHandler.format_currency(user_balance)}",
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def handle_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إدخال المبلغ"""
        user_id = str(update.effective_user.id)
        amount_str = update.message.text
        
        method = context.user_data.get('payment_method')
        transaction_type = context.user_data.get('transaction_type')
        method_info = context.user_data.get('method_info')
        
        if not method or not transaction_type or not method_info:
            await update.message.reply_text("❌ حدث خطأ في المعالجة. يرجى المحاولة مرة أخرى.")
            return
        
        # التحقق من صحة المبلغ
        is_valid, amount, error_msg = PaymentHandler.validate_amount(
            amount_str,
            method_info['min_amount'],
            method_info['max_amount']
        )
        
        if not is_valid:
            await update.message.reply_text(error_msg)
            return
        
        # التحقق من الرصيد للسحب
        if transaction_type == 'withdraw':
            user_balance = context.user_data.get('user_balance', 0)
            if user_balance < amount:
                await update.message.reply_text(
                    f"❌ **رصيدك غير كافي**\n\n"
                    f"💵 رصيدك الحالي: {PaymentHandler.format_currency(user_balance)}\n"
                    f"💸 المبلغ المطلوب: {PaymentHandler.format_currency(amount)}",
                    parse_mode='Markdown'
                )
                return
        
        # حفظ المبلغ في context
        context.user_data['amount'] = amount
        
        # طلب معلومات إضافية بناءً على طريقة الدفع
        await update.message.reply_text(
            f"💰 **المبلغ:** {PaymentHandler.format_currency(amount)}\n\n"
            f"📝 {method_info['instructions']}\n\n"
            f"🔢 **{method_info['input_prompt']}:**",
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة تفاصيل الدفع"""
        user_id = str(update.effective_user.id)
        payment_details = update.message.text
        
        method = context.user_data.get('payment_method')
        transaction_type = context.user_data.get('transaction_type')
        method_info = context.user_data.get('method_info')
        amount = context.user_data.get('amount')
        
        if not all([method, transaction_type, method_info, amount]):
            await update.message.reply_text("❌ حدث خطأ في المعالجة. يرجى المحاولة مرة أخرى.")
            return
        
        # إنشاء مرجع للمعاملة
        reference = PaymentHandler.generate_transaction_reference()
        
        # إنشاء المعاملة في قاعدة البيانات
        transaction_id = store.insertTransaction(
            telegram_id=user_id,
            value=amount,
            action_type=transaction_type,
            provider_type=method,
            transfer_num=payment_details
        )
        
        if not transaction_id:
            await update.message.reply_text("❌ فشل إنشاء المعاملة. يرجى المحاولة مرة أخرى.")
            return
        
        # إعداد رسالة المستخدم
        if transaction_type == 'deposit':
            message = PaymentHandler._create_deposit_message(transaction_id, amount, method_info, reference, payment_details)
        else:
            user = store.getUserByTelegramId(user_id)
            current_balance = user.get('balance', 0) if user else 0
            message = PaymentHandler._create_withdraw_message(transaction_id, amount, method_info, reference, current_balance)
        
        # أزرار التأكيد
        keyboard = [
            [InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f'confirm_{transaction_id}')],
            [InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f'cancel_{transaction_id}')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        # إشعار الإدمن
        await PaymentHandler.notify_admin(transaction_id, transaction_type, user_id, amount, method_info, reference, payment_details, context)
        
        # تنظيف context
        context.user_data.clear()
    
    @staticmethod
    def _create_deposit_message(transaction_id, amount, method_info, reference, payment_details):
        """إنشاء رسالة الإيداع"""
        return f"""
✅ **تم إنشاء طلب الإيداع بنجاح**

🆔 **رقم الطلب:** #{transaction_id}
💰 **المبلغ:** {PaymentHandler.format_currency(amount)}
🏦 **الطريقة:** {method_info['name']} {method_info['emoji']}
🔢 **المرجع:** {reference}
📱 **رقم العملية:** {payment_details}

📝 **تعليمات الدفع تم إرسالها مسبقاً**

⏰ **سيتم مراجعة طلبك خلال 24 ساعة**
✅ **اضغط تأكيد لإرسال الطلب للإدمن**
        """
    
    @staticmethod
    def _create_withdraw_message(transaction_id, amount, method_info, reference, current_balance):
        """إنشاء رسالة السحب"""
        return f"""
✅ **تم إنشاء طلب السحب بنجاح**

🆔 **رقم الطلب:** #{transaction_id}
💸 **المبلغ:** {PaymentHandler.format_currency(amount)}
🏦 **الطريقة:** {method_info['name']} {method_info['emoji']}
🔢 **المرجع:** {reference}
💵 **رصيدك الحالي:** {PaymentHandler.format_currency(current_balance)}

⏰ **سيتم مراجعة طلبك خلال 24 ساعة**
✅ **اضغط تأكيد لإرسال الطلب للإدمن**
        """
    
    @staticmethod
    async def notify_admin(transaction_id, transaction_type, user_id, amount, method_info, reference, payment_details, context):
        """إشعار الإدمن"""
        try:
            admin_id = config.telegram.ADMIN_TELEGRAM_ID
            
            user = store.getUserByTelegramId(user_id)
            user_display = user.get('telegram_username') or user.get('name') or f"المستخدم {user_id}"
            
            if transaction_type == 'deposit':
                title = "💰 طلب إيداع جديد"
                emoji = "💰"
            else:
                title = "💸 طلب سحب جديد"
                emoji = "💸"
            
            admin_message = f"""
{emoji} **{title}**

👤 **المستخدم:** {user_display}
🆔 **المعرف:** {user_id}
{emoji} **المبلغ:** {PaymentHandler.format_currency(amount)}
🏦 **الطريقة:** {method_info['name']} {method_info['emoji']}
🔢 **المرجع:** {reference}
📱 **رقم العملية:** {payment_details}
🆔 **رقم الطلب:** #{transaction_id}
📅 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

اضغط على الزر للمراجعة
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ الموافقة", callback_data=f'admin_approve_{transaction_type}_{transaction_id}'),
                    InlineKeyboardButton("❌ الرفض", callback_data=f'admin_reject_{transaction_type}_{transaction_id}')
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            logger.info(f"تم إرسال إشعار للإدمن بخصوص المعاملة #{transaction_id}")
            
        except Exception as e:
            logger.error(f"فشل إرسال إشعار للإدمن: {e}")
    
    @staticmethod
    def generate_transaction_reference():
        """توليد مرجع المعاملة"""
        timestamp = datetime.now().strftime("%y%m%d%H%M")
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"REF{timestamp}{random_chars}"
    
    @staticmethod
    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استدعاءات المدفوعات"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # معالجة طرق الإيداع
        if data.startswith('deposit_'):
            method = data.replace('deposit_', '')
            await PaymentHandler.process_deposit_request(update, context, method)
        
        # معالجة طرق السحب
        elif data.startswith('withdraw_'):
            method = data.replace('withdraw_', '')
            await PaymentHandler.process_withdraw_request(update, context, method)
        
        # تأكيد الطلب
        elif data.startswith('confirm_'):
            transaction_id = data.replace('confirm_', '')
            await PaymentHandler.confirm_transaction(update, context, transaction_id)
        
        # إلغاء الطلب
        elif data.startswith('cancel_'):
            transaction_id = data.replace('cancel_', '')
            await PaymentHandler.cancel_transaction(update, context, transaction_id)
        
        # موافقة الإدمن
        elif data.startswith('admin_approve_'):
            parts = data.split('_')
            if len(parts) >= 4:
                transaction_type = parts[2]
                transaction_id = parts[3]
                await PaymentHandler.admin_approve_transaction(update, context, transaction_id, transaction_type)
        
        # رفض الإدمن
        elif data.startswith('admin_reject_'):
            parts = data.split('_')
            if len(parts) >= 4:
                transaction_type = parts[2]
                transaction_id = parts[3]
                await PaymentHandler.admin_reject_transaction(update, context, transaction_id, transaction_type)
    
    @staticmethod
    async def confirm_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_id: str):
        """تأكيد المعاملة"""
        await update.callback_query.edit_message_text(
            "✅ **تم تأكيد طلبك**\n\n"
            "⏳ تم إرسال طلبك للمراجعة. سيتم إشعارك عند الموافقة أو الرفض.",
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def cancel_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_id: str):
        """إلغاء المعاملة"""
        # يمكنك هنا تحديث حالة المعاملة في قاعدة البيانات إذا أردت
        await update.callback_query.edit_message_text(
            "❌ **تم إلغاء الطلب**\n\n"
            "تم إلغاء طلبك بنجاح.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')]
            ])
        )
    
    @staticmethod
    async def admin_approve_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_id: str, transaction_type: str):
        """موافقة الإدمن على المعاملة"""
        # التحقق من صلاحية الإدمن
        user_id = str(update.effective_user.id)
        try:
            admin_id = str(config.telegram.ADMIN_TELEGRAM_ID)
            if user_id != admin_id:
                await update.callback_query.answer("❌ ليس لديك صلاحية للقيام بهذا الإجراء", show_alert=True)
                return
        except:
            await update.callback_query.answer("❌ ليس لديك صلاحية للقيام بهذا الإجراء", show_alert=True)
            return
        
        # تحديث حالة المعاملة في قاعدة البيانات
        success = store.update_transaction_status(transaction_id, transaction_type, 'approved')
        
        if success:
            # إذا كان إيداعاً، تحديث رصيد المستخدم
            if transaction_type == 'deposit':
                transaction = store.get_transaction_by_id(transaction_id, transaction_type)
                if transaction:
                    user = store.getUserById(transaction['user_id'])
                    if user:
                        new_balance = user[7] + transaction['value']  # user[7] هو balance في جدول users
                        store.update_user_balance(transaction['user_id'], new_balance)
                        
                        # معالجة أرباح الإحالة
                        try:
                            if transaction['value'] >= 25000:
                                await handlers.referral_system.ReferralSystem.process_referral_earnings(
                                    update, context, transaction['value'], str(transaction['user_id'])
                                )
                        except Exception as e:
                            logger.error(f"Error processing referral earnings: {e}")
            
            await update.callback_query.edit_message_text(
                f"✅ **تمت الموافقة على الطلب #{transaction_id}**\n\n"
                "تم إعلام المستخدم بالموافقة.",
                parse_mode='Markdown'
            )
        else:
            await update.callback_query.edit_message_text(
                "❌ **فشل الموافقة على الطلب**\n\n"
                "يرجى المحاولة مرة أخرى أو مراجعة سجلات النظام.",
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def admin_reject_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_id: str, transaction_type: str):
        """رفض الإدمن للمعاملة"""
        # التحقق من صلاحية الإدمن
        user_id = str(update.effective_user.id)
        try:
            admin_id = str(config.telegram.ADMIN_TELEGRAM_ID)
            if user_id != admin_id:
                await update.callback_query.answer("❌ ليس لديك صلاحية للقيام بهذا الإجراء", show_alert=True)
                return
        except:
            await update.callback_query.answer("❌ ليس لديك صلاحية للقيام بهذا الإجراء", show_alert=True)
            return
        
        # تحديث حالة المعاملة في قاعدة البيانات
        success = store.update_transaction_status(transaction_id, transaction_type, 'rejected')
        
        if success:
            await update.callback_query.edit_message_text(
                f"❌ **تم رفض الطلب #{transaction_id}**\n\n"
                "تم إعلام المستخدم بالرفض.",
                parse_mode='Markdown'
            )
        else:
            await update.callback_query.edit_message_text(
                "❌ **فشل رفض الطلب**\n\n"
                "يرجى المحاولة مرة أخرى أو مراجعة سجلات النظام.",
                parse_mode='Markdown'
            )