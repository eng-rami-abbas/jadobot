from config.telegram import Update 
from telegram.ext import CallbackContext


async def handle_problem_in_website(query):
    text = """في حال ورود مشكلة تقنية ضمن الموقع يرجى التّواصل :
مع الدّعم الرسمي للموقع عبر الرابط 
https://www.ichancy.com/support
أو عبر صفحة الموقع الرّسمية على منصّة Faecbook . 
https://www.facebook.com/jado.ichancy"""
    await query.message.reply_text(text)
