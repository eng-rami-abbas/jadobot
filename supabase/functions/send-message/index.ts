import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

serve(async (req) => {
  const { telegram_id, text } = await req.json();
  const BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
  
  const response = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: telegram_id,
      text: text,
    }),
  });

  const data = await response.json();
  return new Response(JSON.stringify(data), { 
    headers: { "Content-Type": "application/json" } 
  });
});