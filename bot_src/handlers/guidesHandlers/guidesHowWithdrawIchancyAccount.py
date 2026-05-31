from config.telegram import  InlineKeyboardButton, InlineKeyboardMarkup
text = """كيفية سحب رصيد من حساب Ichancy

لسحب رصيد من حسابك في موقع Ichancy عبر البوت، يرجى اتباع الخطوات التالية:

1. اضغط على خيار "Ichancy" في واجهة البوت.

2. اختر "سحب رصيد من حساب Ichancy".

3. أدخل معرّف الحساب أو اسم حساب Ichancy الذي ترغب بالسحب منه.

4. أدخل المبلغ المطلوب سحبه بالدولار ($).

5. انتظر حوالي 15 ثانية حتى تتم معالجة العملية.

✅ تم سحب الرصيد بنجاح."""
async def handle_guides_how_withdraw_ichancy_account(query):
    keyboard = [[InlineKeyboardButton("رجوع للشروحات", callback_data='guides')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
