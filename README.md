# JADO BOT - عجلة الروليت الملكية

## النشر على GitHub Pages + Supabase

1. **رفع الملفات إلى مستودع GitHub**  
   ضع جميع الملفات في فرع `main` وتأكد من تفعيل GitHub Pages من إعدادات المستودع (المسار: `/root` أو `/docs`).

2. **إعداد Supabase**  
   - أنشئ مشروعاً جديداً على [supabase.com](https://supabase.com).  
   - انسخ `SUPABASE_URL` و `SUPABASE_ANON_KEY` إلى ملف `js/supabase.js`.  
   - اذهب إلى SQL Editor ونفذ محتويات `supabase/schema.sql` لإنشاء الجداول.  
   - فعّل Edge Functions من إعدادات المشروع.  
   - ارفع مجلد `supabase/functions` باستخدام Supabase CLI:  
     ```bash
     supabase functions deploy spin-wheel
     supabase functions deploy send-message