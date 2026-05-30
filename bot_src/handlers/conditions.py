from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import supabase_integration as supa


async def handle_terms_and_conditions(source, mode="start"):
    text = """📜 الشروط والأحكام
عند الضغط على زر موافقة فأنت توافق على الشروط القائمة ضمن البوت ويحق لك الإعتراض في حال مواجهة أي مشكلة خارجة عن شروط وقوانين البوت
يرجى قراءة هذه الشّروط قبل استخدام البوت لضمان تجربة آمنة وسلسة:

البوت مخصّص لإنشاء الحسابات، والسّحب، والتعبئة الفورية لحسابات موقع Ichancy.

1_منع الحسابات المتعدّدة:
إنشاء أكثر من حساب للشّخص الواحد مخالف للقوانين، وقد يؤدّي إلى حظر الحسابات المرتبطة وتجميد أرصدتها، وذلك بناءاً على سياسة اللّعب النظيف .

2_تبديل طرق الدفع غير مسموح:
لا يُسمح بشحن رصيد وسحبه بغرض التبديل بين وسائل الدفع المختلفة. في حال اكتشاف عملية كهذه، يتم سحب الرّصيد والتّحفظ عليه دون إشعار مسبق.

3_شروط أرباح الإحالات:
تُحتسب أرباح الإحالة فقط بعد تسجيل 3 إحالات نشطة أو أكثر (أي قاموا بالتعبئة الفعلية).

⛔️تنبيه:
أي محاولة للتّحايل أو مخالفة الشروط ستؤدي إلى إيقاف الحساب وتجميد الأرصدة.)
⚠️ يرجى الموافقة للمتابعة
"""

    if mode == "start":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ موافق", callback_data="agree"),
                InlineKeyboardButton("❌ غير موافق", callback_data="reject")
            ]
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 رجوع إلى القائمة الرئيسية", callback_data="back_to_menu")
            ]
        ])

    if hasattr(source, "message"):
        await source.message.edit_text(text, reply_markup=keyboard)
    else:
        await source.reply_text(text, reply_markup=keyboard)
