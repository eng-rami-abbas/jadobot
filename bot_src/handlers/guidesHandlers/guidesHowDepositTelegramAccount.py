from config.telegram import  InlineKeyboardButton, InlineKeyboardMarkup
text = """كيفية شحن الرصيد ضمن بوت Ichancy

يرجى اتباع الخطوات التالية لإتمام عملية شحن الرصيد بنجاح:

1. اضغط على خيار "شحن رصيد" في واجهة البوت.

2. اختر طريقة الدفع المناسبة لك من بين الخيارات المتاحة.

3. قم بإرسال المبلغ الذي ترغب في شحنه إلى العنوان المخصّص (أقل مبلغ يمكن شحنه هو 1 دولار أمريكي).

4. بعد إتمام التحويل، أدخل كود عملية التحويل، ثم أدخل قيمة المبلغ المرسل.

✅ تم شحن البوت بنجاح."""
async def handle_guides_how_deposit_telegram_account(query):
    keyboard = [[InlineKeyboardButton("رجوع للشروحات", callback_data='guides')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
