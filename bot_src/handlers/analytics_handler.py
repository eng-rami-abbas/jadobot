"""
نظام التحليلات والإحصائيات المتقدمة
"""

import logging
import matplotlib
matplotlib.use('Agg')  # استخدام backend غير تفاعلي
import matplotlib.pyplot as plt
import io
import json
from datetime import datetime, timedelta
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

import store
import config.telegram
from utils import helpers

logger = logging.getLogger(__name__)

class AnalyticsHandler:
    """نظام التحليلات والإحصائيات المتقدمة"""
    
    @staticmethod
    async def admin_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لوحة التحليلات للإدمن"""
        user_id = str(update.effective_user.id)
        
        # التحقق من صلاحية الإدمن
        try:
            admin_id = str(config.telegram.ADMIN_TELEGRAM_ID)
            if user_id != admin_id:
                await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى التحليلات")
                return
        except:
            await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى التحليلات")
            return
        
        # الحصول على الإحصائيات
        stats = await AnalyticsHandler.get_system_stats()
        
        message = f"""
📊 **لوحة التحليلات المتقدمة**

📈 **إحصائيات عامة:**
👥 المستخدمين النشطين: {stats['active_users']}
💰 إجمالي الأرصدة: {stats['total_balance']:,} ليرة
📊 المعاملات اليوم: {stats['today_transactions']}

📅 **نشاط آخر 7 أيام:**
{stats['weekly_activity']}

🎯 **أهم المؤشرات:**
• متوسط الرصيد: {stats['avg_balance']:,} ليرة
• معدل النمو اليومي: {stats['growth_rate']}%
• معدل الاحتفاظ: {stats['retention_rate']}%

🔍 **اختر التقرير المطلوب:**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📈 تقرير المستخدمين", callback_data='analytics_users'),
                InlineKeyboardButton("💰 تقرير المعاملات", callback_data='analytics_transactions')
            ],
            [
                InlineKeyboardButton("📊 تقرير مالي", callback_data='analytics_financial'),
                InlineKeyboardButton("🎯 تقرير أداء", callback_data='analytics_performance')
            ],
            [
                InlineKeyboardButton("📋 تقرير يومي", callback_data='analytics_daily'),
                InlineKeyboardButton("📅 تقرير شهري", callback_data='analytics_monthly')
            ],
            [
                InlineKeyboardButton("📊 رسوم بيانية", callback_data='analytics_charts'),
                InlineKeyboardButton("📤 تصدير بيانات", callback_data='analytics_export')
            ],
            [
                InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def get_system_stats():
        """الحصول على إحصائيات النظام"""
        try:
            # إحصائيات افتراضية (يمكنك استبدالها ببيانات حقيقية)
            stats = {
                'active_users': 150,
                'total_balance': 12500000,
                'today_transactions': 42,
                'weekly_activity': '📊 نشاط جيد - ↗️ 12% نمو',
                'avg_balance': 83333,
                'growth_rate': 5.2,
                'retention_rate': 78.5
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {
                'active_users': 0,
                'total_balance': 0,
                'today_transactions': 0,
                'weekly_activity': '📭 لا توجد بيانات',
                'avg_balance': 0,
                'growth_rate': 0,
                'retention_rate': 0
            }
    
    @staticmethod
    async def generate_user_activity_chart():
        """إنشاء رسم بياني لنشاط المستخدمين"""
        try:
            # بيانات افتراضية
            days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
            new_users = [15, 20, 18, 25, 30, 35, 28]
            active_users = [120, 125, 130, 128, 135, 140, 138]
            
            # إنشاء الرسم البياني
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ax.bar(days, new_users, label='مستخدمين جدد', alpha=0.8)
            ax.plot(days, active_users, label='مستخدمين نشطين', marker='o', linewidth=2)
            
            ax.set_title('نشاط المستخدمين الأسبوعي', fontsize=14, fontname='Arial')
            ax.set_xlabel('اليوم', fontsize=12)
            ax.set_ylabel('عدد المستخدمين', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # تحويل الرسم البياني إلى صورة
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return None
    
    @staticmethod
    async def handle_analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استدعاءات التحليلات"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == 'analytics_users':
            await AnalyticsHandler.show_user_analytics(update, context)
        elif data == 'analytics_transactions':
            await AnalyticsHandler.show_transaction_analytics(update, context)
        elif data == 'analytics_charts':
            await AnalyticsHandler.show_charts(update, context)
        elif data == 'analytics_daily':
            await AnalyticsHandler.show_daily_report(update, context)
        elif data == 'analytics_export':
            await AnalyticsHandler.export_data(update, context)
        else:
            await query.edit_message_text(
                f"📊 **تقرير {data.replace('analytics_', '')}**\n\n"
                "هذا التقرير قيد التطوير وسيتوفر قريباً.\n\n"
                "🔙 العودة للتحليلات",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 التحليلات", callback_data='analytics')]
                ]),
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def show_user_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض تحليلات المستخدمين"""
        query = update.callback_query
        
        message = """
📈 **تقرير تحليلات المستخدمين**

👥 **توزيع المستخدمين:**
• مستخدمين نشطين: 150
• مستخدمين جدد (اليوم): 28
• مستخدمين خاملين: 15

📊 **نمو المستخدمين:**
• معدل النمو اليومي: 5.2%
• معدل الاحتفاظ: 78.5%
• معدل التحويل: 12.3%

🎯 **سلوك المستخدمين:**
• متوسط الرصيد: 83,333 ليرة
• متوسط المعاملات: 3.2/شهر
• وقت النشاط المتوسط: 15 دقيقة

📅 **نشاط الأسبوع:**
الاثنين: 120 نشيط، 15 جديد
الثلاثاء: 125 نشيط، 20 جديد
الأربعاء: 130 نشيط، 18 جديد
الخميس: 128 نشيط، 25 جديد
الجمعة: 135 نشيط، 30 جديد
السبت: 140 نشيط، 35 جديد
الأحد: 138 نشيط، 28 جديد
        """
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 رسم بياني", callback_data='analytics_chart_users')],
                [InlineKeyboardButton("🔙 التحليلات", callback_data='analytics')]
            ]),
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def show_charts(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض الرسوم البيانية"""
        query = update.callback_query
        
        try:
            # إنشاء الرسم البياني
            chart = await AnalyticsHandler.generate_user_activity_chart()
            
            if chart:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=chart,
                    caption="📊 **رسم بياني لنشاط المستخدمين**\n\n🔙 العودة للتحليلات",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 التحليلات", callback_data='analytics')]
                    ])
                )
            else:
                await query.answer("❌ حدث خطأ في إنشاء الرسم البياني", show_alert=True)
        except Exception as e:
            logger.error(f"Error showing chart: {e}")
            await query.answer("❌ حدث خطأ في عرض الرسم البياني", show_alert=True)
    
    @staticmethod
    async def show_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تقرير يومي"""
        query = update.callback_query
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        message = f"""
📋 **التقرير اليومي - {today}**

📈 **المؤشرات الرئيسية:**
👥 المستخدمين النشطين: 150 (+12)
💰 إجمالي الأرصدة: 12,500,000 (+850,000)
📊 المعاملات: 42 (+8)

💵 **الإيرادات:**
• إيداعات اليوم: 1,250,000 ليرة
• عمولات اليوم: 125,000 ليرة
• أرباح اليوم: 375,000 ليرة

👥 **النمو:**
• مستخدمين جدد: 28
• إحالات جديدة: 15
• أرباح الإحالة: 75,000 ليرة

🎯 **الأهداف اليومية:**
• الإيداعات: ✅ متجاوز
• المستخدمين الجدد: ✅ متجاوز
• الإيرادات: ✅ متجاوز

📊 **مقارنة بالأمس:**
• النمو: ↗️ 12%
• الإيرادات: ↗️ 15%
• النشاط: ↗️ 8%
        """
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 تصدير PDF", callback_data='export_daily_pdf')],
                [InlineKeyboardButton("📧 إرسال للإدارة", callback_data='send_daily_report')],
                [InlineKeyboardButton("🔙 التحليلات", callback_data='analytics')]
            ]),
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تصدير البيانات"""
        query = update.callback_query
        
        # إنشاء بيانات افتراضية للتجربة
        data = {
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "active_users": 150,
            "total_balance": 12500000,
            "today_transactions": 42,
            "growth_rate": 5.2,
            "daily_revenue": 1250000
        }
        
        # تحويل إلى JSON
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        
        # إرسال كملف
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=io.BytesIO(json_data.encode()),
            filename=f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            caption="📤 **تم تصدير بيانات التحليلات**\n\n🔙 العودة للتحليلات",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 التحليلات", callback_data='analytics')]
            ])
        )

# دالة مساعدة للاستخدام في bot.py
async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأمر /analytics"""
    await AnalyticsHandler.admin_analytics(update, context)