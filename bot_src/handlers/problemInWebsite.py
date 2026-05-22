from config.telegram import Update 
from telegram.ext import CallbackContext


async def handle_problem_in_website(query):
    text = """في حال ورود مشكلة تقنية ضمن الموقع يرجى التّواصل :
مع الدّعم الرسمي للموقع عبر الرابط 
https://direct.lc.chat/16220229/
أو عبر صفحة الموقع الرّسمية على منصّة Faecbook . 
https://www.facebook.com/ichancy.co?mibextid=ZbWKwL"""
    await query.message.reply_text(text)