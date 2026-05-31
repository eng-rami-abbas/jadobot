from config.telegram import  InlineKeyboardButton, InlineKeyboardMarkup
text = """كيفية شحن رصيد ضمن حساب Ichancy
لشحن رصيد إلى حسابك في موقع Ichancy عبر البوت، يرجى اتباع الخطوات التالية:

1. اضغط على خيار "Ichancy" في واجهة البوت.

2. اختر "شحن حساب Ichancy".

3. أدخل معرّف الحساب أو اسم حساب Ichancy الذي ترغب بشحنه.

4. أدخل المبلغ المطلوب شحنه بالليرة السوريّة .

5. انتظر حوالي 15 ثانية حتى تتم معالجة العملية.

✅ تم شحن الحساب بنجاح."""
async def handle_guides_how_deposit_ichancy_account(query):
    keyboard = [[InlineKeyboardButton("رجوع للشروحات", callback_data='guides')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
