import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" };

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const { telegram_id, action } = await req.json();
  const supabaseClient = createClient(
    Deno.env.get("SUPABASE_URL") ?? "",
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
  );

  // جلب المستخدم
  const { data: user, error: userError } = await supabaseClient
    .from("users")
    .select("*")
    .eq("telegram_id", telegram_id)
    .single();

  if (userError || !user) {
    return new Response(JSON.stringify({ error: "User not found" }), { headers: corsHeaders, status: 404 });
  }

  // التحقق من الأهلية
  if (action === "check_eligibility") {
    // هل لديه أي إيداع؟
    const { count: depositCount } = await supabaseClient
      .from("deposits")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id);

    if (!depositCount || depositCount === 0) {
      return new Response(JSON.stringify({ allowed: false, message: "يجب القيام بإيداع أولاً للحصول على تدويرة مجانية" }), { headers: corsHeaders });
    }

    // التحقق من التدويرة اليومية (إذا لم تكن هناك تدويرات إضافية)
    if (user.free_spins_remaining > 0) {
      return new Response(JSON.stringify({ allowed: true }), { headers: corsHeaders });
    }

    const today = new Date().toISOString().split("T")[0];
    if (user.last_spin_date === today) {
      return new Response(JSON.stringify({ allowed: false, message: "لقد استخدمت تدويرتك اليومية، عد غداً" }), { headers: corsHeaders });
    }

    return new Response(JSON.stringify({ allowed: true }), { headers: corsHeaders });
  }

  // تنفيذ التدوير
  if (action === "spin") {
    // استهلاك تدويرة إضافية أو تدويرة يومية
    if (user.free_spins_remaining > 0) {
      await supabaseClient.from("users").update({ free_spins_remaining: user.free_spins_remaining - 1 }).eq("id", user.id);
    } else {
      const today = new Date().toISOString().split("T")[0];
      await supabaseClient.from("users").update({ last_spin_date: today }).eq("id", user.id);
    }

    // تحديد الجائزة عشوائياً (آمن على الخادم)
    const prizes = [
      { type: "money", value: 10000, segment: 0 },
      { type: "money", value: 20000, segment: 1 },
      { type: "lose", segment: 2 },
      { type: "premium", segment: 3 },
      { type: "money", value: 50000, segment: 4 },
      { type: "bonus", value: 5, segment: 5 },
      { type: "lose", segment: 6 },
      { type: "free_spin", segment: 7 },
    ];

    // توزيع احتمالي (يمكن تعديله)
    const weights = [10, 8, 25, 2, 5, 10, 25, 15]; // مجموع 100
    const totalWeight = weights.reduce((a,b)=>a+b,0);
    const rand = Math.random() * totalWeight;
    let cumulative = 0;
    let selectedPrize = prizes[0];
    for (let i=0; i<prizes.length; i++) {
      cumulative += weights[i];
      if (rand < cumulative) {
        selectedPrize = prizes[i];
        break;
      }
    }

    // معالجة الجائزة وتسجيلها
    const { type, value, segment } = selectedPrize;
    let message = "";

    if (type === "money") {
      await supabaseClient.from("users").update({ balance: user.balance + value }).eq("id", user.id);
      await supabaseClient.from("spins").insert({ user_id: user.id, result_type: "money", result_value: value });
      message = `🎉 مبروك لقد ربحت ${value} عملة!`;
    } else if (type === "bonus") {
      await supabaseClient.from("users").update({ bonus_active: true, bonus_percentage: value }).eq("id", user.id);
      await supabaseClient.from("spins").insert({ user_id: user.id, result_type: "bonus", result_value: value });
      message = `🎉 مبروك لقد ربحت Bonus ${value}% على إيداعك القادم!`;
    } else if (type === "free_spin") {
      await supabaseClient.from("users").update({ free_spins_remaining: user.free_spins_remaining + 1 }).eq("id", user.id);
      await supabaseClient.from("spins").insert({ user_id: user.id, result_type: "free_spin", result_value: 0 });
      message = "🎉 مبروك حصلت على إعادة تدوير مجانية!";
    } else if (type === "premium") {
      await supabaseClient.from("premium_rewards").insert({ user_id: user.id });
      await supabaseClient.from("spins").insert({ user_id: user.id, result_type: "premium", result_value: 0 });
      message = "🎉 مبروك لقد ربحت Telegram Premium! سيتم التواصل معك.";
    } else { // lose
      await supabaseClient.from("spins").insert({ user_id: user.id, result_type: "lose", result_value: 0 });
      message = "😔 حظ أوفر، نتمنى لك حظاً أفضل غداً";
    }

    return new Response(JSON.stringify({
      segment_index: segment,
      prize_type: type,
      prize_value: value || 0,
      message,
    }), { headers: corsHeaders });
  }

  return new Response(JSON.stringify({ error: "Invalid action" }), { headers: corsHeaders, status: 400 });
});