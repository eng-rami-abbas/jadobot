# ملف إصلاح شامل لجميع مشاكل بوت JadoBot
# ================================
# هذا الملف يحتوي على جميع التغييرات المطلوبة
# ================================

# ============================================================
# الإصلاح 1: handlers/button.py
# المشكلة: import handlers.wheel_handler داخل الدالة button() 
#           يسبب UnboundLocalError لكل المراجع handlers.xxx
# الحل: نقل الاستيراد إلى أعلى الملف مع باقي الاستيرادات
# ============================================================

# التغيير المطلوب في handlers/button.py:
# في السطر ~229 داخل الدالة button() يوجد:
#   import handlers.wheel_handler
# هذا السطر يجب أن يُحذف من داخل الدالة ويُنقل إلى أعلى الملف
# مع باقي استيرادات handlers

# التغيير:
# أضف في أعلى الملف (بعد سطر import handlers.log):
#   import handlers.wheel_handler
# واحذف السطر من داخل الدالة button()


# ============================================================
# الإصلاح 2: جميع ملفات ConversationHandler - إضافة per_message=True
# المشكلة: CallbackQueryHandler لا يعمل بدون per_message=True
# ============================================================

# --- handlers/reseiveGifts.py ---
# تغيير:
#   conv_handler = ConversationHandler(
#       entry_points=[...],
#       states={...},
#       fallbacks=[...],
#   )
# إلى:
#   conv_handler = ConversationHandler(
#       entry_points=[...],
#       states={...},
#       fallbacks=[...],
#       per_message=True,
#       per_user=True,
#       allow_reentry=True,
#   )

# --- handlers/gift_code.py ---
# تغيير:
#   return ConversationHandler(
#       ...,
#       allow_reentry=True,
#       per_user=True
#   )
# إلى:
#   return ConversationHandler(
#       ...,
#       allow_reentry=True,
#       per_user=True,
#       per_message=True,
#   )

# --- handlers/depositAccount.py ---
# تغيير:
#   conv_handler = ConversationHandler(
#       entry_points=[...],
#       states={...},
#       fallbacks=[...],
#   )
# إلى:
#   conv_handler = ConversationHandler(
#       entry_points=[...],
#       states={...},
#       fallbacks=[...],
#       per_message=True,
#       per_user=True,
#       allow_reentry=True,
#   )

# --- handlers/withdrawalAccount.py ---
# نفس التغيير كما depositAccount.py

# --- handlers/adminMessage.py ---
# نفس التغيير كما depositAccount.py

# --- handlers/deposit.py ---
# تغيير:
#   return ConversationHandler(
#       ...,
#       allow_reentry=True,
#       per_user=True
#   )
# إلى:
#   return ConversationHandler(
#       ...,
#       allow_reentry=True,
#       per_user=True,
#       per_message=True,
#   )

# --- handlers/withdrawal_conversation.py ---
# نفس التغيير كما deposit.py

# --- handlers/sendGifts.py ---
# نفس التغيير كما deposit.py

# --- handlers/support_system.py ---
# تغيير:
#   return ConversationHandler(
#       entry_points=[...],
#       states={...},
#       fallbacks=[...],
#   )
# إلى:
#   return ConversationHandler(
#       entry_points=[...],
#       states={...},
#       fallbacks=[...],
#       per_message=True,
#       per_user=True,
#       allow_reentry=True,
#   )

# --- handlers/createAccount.py ---
# تغيير:
#   conv_handler = ConversationHandler(
#       entry_points=[...],
#       states={...},
#       fallbacks=[...],
#   )
# إلى:
#   conv_handler = ConversationHandler(
#       entry_points=[...],
#       states={...},
#       fallbacks=[...],
#       per_message=True,
#       per_user=True,
#       allow_reentry=True,
#   )


# ============================================================
# الإصلاح 3: store.py - تهيئة قاعدة البيانات عند الاستيراد
# المشكلة: "no such table: users" لأن init_db() لا يُستدعى
# الحل: إضافة استدعاء init_db() عند استيراد الموديول
# ============================================================

# أضف بعد دالة migrate_db():
#   # تهيئة قاعدة البيانات عند استيراد الموديول
#   try:
#       init_db()
#   except Exception as e:
#       print(f"Warning: Could not initialize SQLite database: {e}")


# ============================================================
# الإصلاح 4: supabase_integration.py - إزالة الدوال المكررة + إصلاح upsert
# المشكلة: get_wheel_extra_spins و set_wheel_extra_spins معرّفتان مرتين
# المشكلة: upsert_ichancy_details لا يحدد on_conflict
# ============================================================

# 1. احذف الدالتين المكررتين (النسخة الثانية من كل منهما)
# 2. أضف on_conflict لـ upsert_ichancy_details:
#    return get_client().table("users_ichancy_details").upsert(
#        account_data, on_conflict="telegram_id"
#    ).execute()


# ============================================================
# الإصلاح 5: services/iChancyAPI.py - إزالة الكود الميت
# المشكلة: دالة _sign_in تحتوي على كود مكرر بعد return False
# الحل: حذف الأسطر 183-224 (الكود الميت بعد return)
# ============================================================

# في دالة _sign_in، بعد السطر:
#   return False
# داخل الـ except block، هناك كود مكرر غير قابل للتنفيذ
# احذفه بالكامل


# ============================================================
# الإصلاح 6: bot.py - استدعاء init_db() عند بدء البوت
# ============================================================

# أضف في بداية دالة main() بعد التحقق من TOKEN:
#   # تهيئة قاعدة بيانات SQLite
#   try:
#       import store
#       store.init_db()
#       print("SQLite database initialized")
#   except Exception as e:
#       print(f"Warning: SQLite init error: {e}")
