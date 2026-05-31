from config.telegram import  InlineKeyboardButton, InlineKeyboardMarkup
text = """كيفيّة سحب الرصيد من بوت Ichancy

لإتمام عملية السحب بنجاح، يرجى اتباع الخطوات التالية:

1. اضغط على خيار "سحب رصيد" من واجهة البوت.

2. اختر طريقة السحب المناسبة لك من بين الوسائل المتاحة.

3. أدخل بياناتك المطلوبة بدقة، بحسب الطريقة التي قمت باختيارها.

4. أدخل المبلغ الذي ترغب بسحبه.

✅ تم تنفيذ عملية السحب بنجاح.
يتم معالجة طلب السحب خلال مدة أقصاها نصف ساعة."""
async def handle_guides_how_withdraw_telegram_account(query):
    keyboard = [[InlineKeyboardButton("رجوع للشروحات", callback_data='guides')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
