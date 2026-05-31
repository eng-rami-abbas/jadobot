"""
أدوات مساعدة للبوت
"""

import re
import random
import string
from datetime import datetime, timedelta

def format_currency(amount: int) -> str:
    """تنسيق العملة"""
    return f"{amount:,}"

def validate_amount(amount_str: str, min_amount: int = 0, max_amount: int = 1000000000) -> tuple:
    """التحقق من صحة المبلغ"""
    try:
        amount = int(amount_str)
        
        if amount <= 0:
            return False, 0, "❌ المبلغ يجب أن يكون أكبر من صفر"
        
        if amount < min_amount:
            return False, 0, f"❌ الحد الأدنى هو {format_currency(min_amount)}"
        
        if amount > max_amount:
            return False, 0, f"❌ الحد الأقصى هو {format_currency(max_amount)}"
        
        return True, amount, ""
        
    except ValueError:
        return False, 0, "❌ يرجى إدخال مبلغ صحيح"

def get_user_display_name(user: dict) -> str:
    """الحصول على اسم المستخدم للعرض"""
    if user.get('telegram_username'):
        return f"@{user['telegram_username']}"
    elif user.get('name'):
        return user['name']
    else:
        return f"المستخدم {user.get('telegram_id', 'غير معروف')}"

def format_transaction_type(transaction_type: str) -> str:
    """تنسيق نوع المعاملة"""
    types = {
        "deposit": "💰 إيداع",
        "withdraw": "💸 سحب",
        "referral": "👥 إحالة",
        "gift": "🎁 هدية",
        "gift_code": "🎁 كود هدية",
        "manual": "⚙️ يدوي"
    }
    return types.get(transaction_type, transaction_type)

def format_transaction_status(status: str) -> str:
    """تنسيق حالة المعاملة"""
    statuses = {
        "pending": "⏳ قيد المراجعة",
        "completed": "✅ مكتملة",
        "failed": "❌ فاشلة",
        "cancelled": "🚫 ملغية"
    }
    return statuses.get(status, status)

def format_datetime(dt) -> str:
    """تنسيق التاريخ والوقت"""
    if not dt:
        return "غير محدد"
    
    if isinstance(dt, str):
        return dt
    
    try:
        now = datetime.now()
        diff = now - dt
        
        if diff.days == 0:
            if diff.seconds < 3600:  # أقل من ساعة
                minutes = diff.seconds // 60
                return f"منذ {minutes} دقيقة"
            else:  # أقل من يوم
                hours = diff.seconds // 3600
                return f"منذ {hours} ساعة"
        elif diff.days == 1:
            return "أمس"
        elif diff.days < 7:
            return f"منذ {diff.days} أيام"
        else:
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt)

def validate_telegram_id(telegram_id_str: str) -> tuple:
    """التحقق من صحة معرف التيليجرام"""
    try:
        telegram_id = int(telegram_id_str)
        if telegram_id <= 0:
            return False, "", "❌ معرف التيليجرام يجب أن يكون رقم موجب"
        return True, str(telegram_id), ""
    except ValueError:
        return False, "", "❌ معرف التيليجرام يجب أن يكون رقم"

def validate_username(username: str) -> tuple:
    """التحقق من صحة اسم المستخدم"""
    # إزالة @ إذا كانت موجودة
    if username.startswith('@'):
        username = username[1:]
    
    # التحقق من صحة اسم المستخدم
    if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
        return False, "", "❌ اسم المستخدم يجب أن يحتوي على 5-32 حرف (أحرف إنجليزية وأرقام و _ فقط)"
    
    return True, username, ""

def generate_referral_code(length: int = 8) -> str:
    """توليد كود إحالة"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def format_phone_number(phone: str) -> str:
    """تنسيق رقم الهاتف للعرض"""
    phone = re.sub(r'[^\d]', '', phone)
    if len(phone) == 9 and phone.startswith('9'):
        return f"+963 {phone}"
    elif len(phone) == 10 and phone.startswith('09'):
        return f"+963 {phone[1:]}"
    elif len(phone) == 12 and phone.startswith('963'):
        return f"+{phone[:3]} {phone[3:]}"
    return phone

def escape_markdown(text: str) -> str:
    """تجنب رموز الماركداون"""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

def truncate_text(text: str, max_length: int = 100) -> str:
    """اختصار النص"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def calculate_referral_earnings(deposit_amount: int, referral_percentage: int = 10) -> int:
    """حساب أرباح الإحالة"""
    return int(deposit_amount * (referral_percentage / 100))

def generate_transaction_reference():
    """توليد مرجع المعاملة"""
    timestamp = datetime.now().strftime("%y%m%d%H%M")
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"REF{timestamp}{random_chars}"

def get_time_range_filter(range_type: str) -> tuple:
    """الحصول على فلتر النطاق الزمني"""
    now = datetime.now()
    
    if range_type == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif range_type == "week":
        start = now - timedelta(days=7)
        end = now
    elif range_type == "month":
        start = now - timedelta(days=30)
        end = now
    elif range_type == "year":
        start = now - timedelta(days=365)
        end = now
    else:  # all
        start = datetime(2020, 1, 1)
        end = now
    
    return start, end

def is_valid_amount_format(amount_str: str) -> bool:
    """التحقق من تنسيق المبلغ"""
    try:
        float(amount_str)
        return True
    except ValueError:
        return False

def clean_phone_number(phone: str) -> str:
    """تنظيف رقم الهاتف"""
    # إزالة جميع الرموز غير الرقمية
    phone = re.sub(r'[^\d]', '', phone)
    
    # إضافة رمز البلد إذا لم يكن موجود
    if phone.startswith('9') and len(phone) == 9:
        phone = '963' + phone
    elif phone.startswith('09') and len(phone) == 10:
        phone = '963' + phone[1:]
    
    return phone

def paginate_list(items, page: int = 1, per_page: int = 10):
    """تقسيم القائمة إلى صفحات"""
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page
    
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages
    
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    
    return items[start_index:end_index], page, total_pages

def format_transaction_history(transactions, page: int = 1, per_page: int = 10) -> str:
    """تنسيق سجل المعاملات"""
    if not transactions:
        return "📭 لا توجد معاملات"
    
    paginated_transactions, current_page, total_pages = paginate_list(transactions, page, per_page)
    
    message = f"📜 سجل المعاملات (صفحة {current_page}/{total_pages})\n\n"
    
    for transaction in paginated_transactions:
        message += f"""
{format_transaction_type(transaction.get('action_type', 'معاملة'))} {format_currency(transaction.get('value', 0))}
{format_transaction_status(transaction.get('status', 'غير معروف'))}
{format_datetime(transaction.get('created_at'))} 📅
{'📝 ' + transaction.get('description', '') if transaction.get('description') else ''}
{'━' * 30}
        """
    
    return message.strip()