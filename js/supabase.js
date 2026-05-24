// supabase.js
const SUPABASE_URL = 'https://kpnxtvargeajpxgswdso.supabase.co'; // 
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtwbnh0dmFyZ2VhanB4Z3N3ZHNvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1MTM1NDgsImV4cCI6MjA5MjA4OTU0OH0.nLWI13zA_60KixjgE-ErieCuaSg3D756zRW_FqwOh-g'; //

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// دالة مساعدة لاستدعاء Edge Function
async function callEdgeFunction(functionName, body) {
  const { data, error } = await supabase.functions.invoke(functionName, {
    body: JSON.stringify(body),
  });
  if (error) throw error;
  return data;
}