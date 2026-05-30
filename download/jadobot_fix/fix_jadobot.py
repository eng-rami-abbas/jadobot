#!/usr/bin/env python3
"""
سكريبت إصلاح شامل لبوت JadoBot
يشغل هذا السكريبت في جذر مجلد bot_src ويقوم بجميع الإصلاحات المطلوبة

الاستخدام:
    python fix_jadobot.py

الإصلاحات:
1. إصلاح UnboundLocalError في button.py (نقل استيراد wheel_handler)
2. إضافة per_message=True لجميع ConversationHandler (9 ملفات)
3. تهيئة SQLite database عند استيراد store.py
4. إزالة الدوال المكررة في supabase_integration.py
5. إصلاح upsert_ichancy_details بإضافة on_conflict
6. إضافة استدعاء init_db() في bot.py
"""

import os
import re
import sys


def fix_button_py():
    """إصلاح 1: نقل import handlers.wheel_handler من داخل الدالة إلى أعلى الملف"""
    filepath = "handlers/button.py"
    if not os.path.exists(filepath):
        print(f"❌ ملف {filepath} غير موجود")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. إضافة import handlers.wheel_handler بعد import handlers.log
    if 'import handlers.wheel_handler' not in content.split('async def button')[0]:
        content = content.replace(
            'import handlers.log\n',
            'import handlers.log\nimport handlers.wheel_handler  # ← تم النقل لحل مشكلة UnboundLocalError\n'
        )
    
    # 2. حذف الاستيراد من داخل الدالة button()
    # البحث عن النمط: import handlers.wheel_handler داخل الدالة
    content = re.sub(
        r'\s+import handlers\.wheel_handler\s*\n',
        '  # ← تم نقل الاستيراد إلى أعلى الملف لحل مشكلة UnboundLocalError\n',
        content
    )
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ تم إصلاح {filepath} - نقل استيراد wheel_handler إلى أعلى الملف")
        return True
    else:
        print(f"⚠️ لم يتم العثور على التغيير المطلوب في {filepath}")
        return False


def fix_conversation_handlers():
    """إصلاح 2: إضافة per_message=True لجميع ConversationHandler"""
    
    # الملفات التي تحتاج per_message=True + per_user=True + allow_reentry=True
    files_need_all = [
        "handlers/reseiveGifts.py",
        "handlers/depositAccount.py",
        "handlers/withdrawalAccount.py",
        "handlers/adminMessage.py",
        "handlers/support_system.py",
        "handlers/createAccount.py",
    ]
    
    # الملفات التي لديها per_user=True و allow_reentry=True لكن تنقصها per_message=True
    files_need_per_message = [
        "handlers/gift_code.py",
        "handlers/deposit.py",
        "handlers/withdrawal_conversation.py",
        "handlers/sendGifts.py",
    ]
    
    fixed_count = 0
    
    for filepath in files_need_all:
        if not os.path.exists(filepath):
            print(f"⚠️ ملف {filepath} غير موجود")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # البحث عن ConversationHandler الذي لا يحتوي على per_message
        # وإضافة per_message=True, per_user=True, allow_reentry=True
        
        # النمط 1: fallbacks=[CommandHandler('cancel', cancel)],\n    )
        # نضيف قبل الإغلاق
        if 'per_message=True' not in content:
            # إضافة بعد fallbacks مباشرة قبل إغلاق ConversationHandler
            content = re.sub(
                r'(ConversationHandler\([^)]*fallbacks=\[[^\]]*\],\s*\n\s*)(\))',
                r'\1    per_message=True,\n    per_user=True,\n    allow_reentry=True,\n\2',
                content,
                flags=re.DOTALL
            )
            
            # إذا لم يعمل النمط الأول، نحاول نمط آخر
            if 'per_message=True' not in content:
                content = re.sub(
                    r'(fallbacks=\[[^\]]*\],)(\s*\n\s*\))',
                    r'\1\n        per_message=True,\n        per_user=True,\n        allow_reentry=True,\2',
                    content
                )
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ تم إصلاح {filepath} - إضافة per_message=True, per_user=True, allow_reentry=True")
            fixed_count += 1
        else:
            print(f"⚠️ لم يتم تطبيق التغيير على {filepath} - قد يحتاج إصلاح يدوي")
    
    for filepath in files_need_per_message:
        if not os.path.exists(filepath):
            print(f"⚠️ ملف {filepath} غير موجود")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        if 'per_message=True' not in content:
            # إضافة per_message=True بعد per_user=True
            content = content.replace(
                'per_user=True',
                'per_user=True,\n        per_message=True'
            )
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ تم إصلاح {filepath} - إضافة per_message=True")
            fixed_count += 1
        else:
            print(f"⚠️ لم يتم تطبيق التغيير على {filepath}")
    
    return fixed_count


def fix_store_py():
    """إصلاح 3: تهيئة قاعدة البيانات عند استيراد store.py"""
    filepath = "store.py"
    if not os.path.exists(filepath):
        print(f"❌ ملف {filepath} غير موجود")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'init_db()  # تهيئة تلقائية' in content:
        print(f"✅ {filepath} تم إصلاحه مسبقاً")
        return True
    
    # إضافة استدعاء init_db() بعد تعريف دالة migrate_db
    insert_after = 'def migrate_db():'
    
    # البحث عن نهاية دالة migrate_db وإضافة init_db() بعدها
    # نبحث عن آخر def بعد migrate_db
    pattern = r"(def migrate_db\(\):.*?)(\n# =+\n# USERS)"
    
    replacement = r"""\1

# ← إصلاح: تهيئة قاعدة البيانات عند استيراد الموديول
# هذا يضمن أن الجداول موجودة قبل أي عملية إدراج
try:
    init_db()  # تهيئة تلقائية
except Exception as e:
    print(f"Warning: Could not initialize SQLite database: {e}")

\2"""
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ تم إصلاح {filepath} - إضافة استدعاء init_db() تلقائي")
        return True
    
    # طريقة بديلة: إضافة بعد migrate_db إذا لم يعمل النمط الأول
    # نبحث عن أول دالة بعد migrate_db
    if "try:\n    init_db()" not in content:
        # إضافة قبل دالة getUserByTelegramId
        content = content.replace(
            '\n# =========================\n# USERS\n# =========================\n\ndef getUserByTelegramId',
            '\n# ← إصلاح: تهيئة قاعدة البيانات عند استيراد الموديول\ntry:\n    init_db()  # تهيئة تلقائية\nexcept Exception as e:\n    print(f"Warning: Could not initialize SQLite database: {e}")\n\n# =========================\n# USERS\n# =========================\n\ndef getUserByTelegramId'
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ تم إصلاح {filepath} - إضافة استدعاء init_db() تلقائي")
        return True
    
    print(f"⚠️ لم يتم تطبيق التغيير على {filepath}")
    return False


def fix_supabase_integration():
    """إصلاح 4: إزالة الدوال المكررة + إصلاح upsert_ichancy_details"""
    filepath = "supabase_integration.py"
    if not os.path.exists(filepath):
        print(f"❌ ملف {filepath} غير موجود")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. إصلاح upsert_ichancy_details - إضافة on_conflict
    content = content.replace(
        'return get_client().table("users_ichancy_details").upsert(account_data).execute()',
        'return get_client().table("users_ichancy_details").upsert(account_data, on_conflict="telegram_id").execute()'
    )
    
    # 2. إزالة الدوال المكررة (get_wheel_extra_spins و set_wheel_extra_spins)
    # نبحث عن النسخة الثانية من كل دالة ونحذفها
    lines = content.split('\n')
    new_lines = []
    skip_until_next_def = False
    seen_functions = set()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # التحقق من دالة مكررة
        func_match = re.match(r'^def (get_wheel_extra_spins|set_wheel_extra_spins)\(', line)
        if func_match:
            func_name = func_match.group(1)
            if func_name in seen_functions:
                # هذه نسخة مكررة - تخطيها حتى الدالة التالية
                skip_until_next_def = True
                i += 1
                continue
            else:
                seen_functions.add(func_name)
        
        if skip_until_next_def:
            # تخطي الأسطر حتى نصل إلى دالة جديدة أو نهاية الملف
            if line.startswith('def ') and not re.match(r'^def (get_wheel_extra_spins|set_wheel_extra_spins)\(', line):
                skip_until_next_def = False
                new_lines.append(line)
            elif line.strip() == '' and i + 1 < len(lines) and lines[i + 1].startswith('def '):
                skip_until_next_def = False
                new_lines.append(line)
            i += 1
            continue
        
        new_lines.append(line)
        i += 1
    
    content = '\n'.join(new_lines)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ تم إصلاح {filepath} - إزالة الدوال المكررة + إضافة on_conflict")
        return True
    
    print(f"⚠️ لم يتم تطبيق التغيير على {filepath}")
    return False


def fix_bot_py():
    """إصلاح 6: إضافة استدعاء store.init_db() في bot.py"""
    filepath = "bot.py"
    if not os.path.exists(filepath):
        print(f"❌ ملف {filepath} غير موجود")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'store.init_db()' in content:
        print(f"✅ {filepath} تم إصلاحه مسبقاً")
        return True
    
    # إضافة بعد "Bot starting..."
    content = content.replace(
        'print("Bot starting...")',
        'print("Bot starting...")\n\n    # تهيئة قاعدة بيانات SQLite\n    try:\n        import store\n        store.init_db()\n        print("SQLite database initialized")\n    except Exception as e:\n        print(f"Warning: SQLite init error: {e}")'
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ تم إصلاح {filepath} - إضافة استدعاء store.init_db()")
    return True


def main():
    print("=" * 60)
    print("🔧 سكريبت إصلاح شامل لبوت JadoBot")
    print("=" * 60)
    print()
    
    # التحقق من أننا في المجلد الصحيح
    if not os.path.exists("bot.py") and not os.path.exists("handlers"):
        print("❌ يرجى تشغيل هذا السكريبت من داخل مجلد bot_src")
        print("   cd bot_src && python fix_jadobot.py")
        sys.exit(1)
    
    fixes_applied = 0
    
    print("📋 الإصلاح 1: UnboundLocalError في button.py")
    print("-" * 40)
    if fix_button_py():
        fixes_applied += 1
    print()
    
    print("📋 الإصلاح 2: إضافة per_message=True لجميع ConversationHandler")
    print("-" * 40)
    count = fix_conversation_handlers()
    fixes_applied += count
    print()
    
    print("📋 الإصلاح 3: تهيئة SQLite عند استيراد store.py")
    print("-" * 40)
    if fix_store_py():
        fixes_applied += 1
    print()
    
    print("📋 الإصلاح 4: إصلاح supabase_integration.py")
    print("-" * 40)
    if fix_supabase_integration():
        fixes_applied += 1
    print()
    
    print("📋 الإصلاح 5: إضافة store.init_db() في bot.py")
    print("-" * 40)
    if fix_bot_py():
        fixes_applied += 1
    print()
    
    print("=" * 60)
    print(f"✅ تم تطبيق {fixes_applied} إصلاح بنجاح!")
    print()
    print("⚠️ ملاحظات مهمة:")
    print("1. مشكلة iChancy API 403 تحتاج مراجعة بيانات الدخول")
    print("   أو استخدام VPN/Proxy في Railway")
    print("2. يجب التأكد من وجود جدول users_ichancy_details في Supabase")
    print("3. يجب إعادة رفع الكود إلى GitHub بعد الإصلاح")
    print("=" * 60)


if __name__ == '__main__':
    main()
