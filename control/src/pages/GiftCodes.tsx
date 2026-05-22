import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";
import { useApp } from "../contexts/GlobalContext";

type GiftCode = {
  code: string;
  amount: number;
  used: boolean;
  expires_at: string;
};

export default function GiftCodes() {
  const { language, theme } = useApp();
  const isDark = theme === "dark";

  const [codes, setCodes] = useState<GiftCode[]>([]);
  const [code, setCode] = useState("");
  const [amount, setAmount] = useState<number | "">("");
  const [loading, setLoading] = useState(false);

  const t = {
    title: language === "ar" ? "🎁 أكواد الهدية" : "🎁 Gift Codes",
    subtitle: language === "ar" ? "إنشاء وإدارة الأكواد" : "Create and manage gift codes",
    create: language === "ar" ? "إنشاء كود" : "Create Code",
    code: language === "ar" ? "الكود" : "Code",
    amount: language === "ar" ? "المبلغ" : "Amount",
    status: language === "ar" ? "الحالة" : "Status",
    expire: language === "ar" ? "الانتهاء" : "Expires",
    action: language === "ar" ? "إجراء" : "Action",
    used: language === "ar" ? "مستخدم" : "Used",
    available: language === "ar" ? "متاح" : "Available",
    delete: language === "ar" ? "حذف" : "Delete",
    empty: language === "ar" ? "لا يوجد أكواد" : "No codes yet",
  };

  const fetchCodes = async () => {
    const { data } = await supabase
      .from("gift_codes")
      .select("*")
      .order("expires_at", { ascending: false });

    if (data) setCodes(data);
  };

  useEffect(() => {
    fetchCodes();
  }, []);

  const createCode = async () => {
    if (!code || !amount) return;

    setLoading(true);

    const expiresAt = new Date();
    expiresAt.setHours(expiresAt.getHours() + 72);

    await supabase.from("gift_codes").insert([
      {
        code,
        amount: Number(amount),
        expires_at: expiresAt.toISOString(),
        used: false,
      },
    ]);

    setLoading(false);
    setCode("");
    setAmount("");
    fetchCodes();
  };

  const deleteCode = async (codeId: string) => {
    await supabase.from("gift_codes").delete().eq("code", codeId);
    fetchCodes();
  };

  return (
    <div className="space-y-6">
      
      {/* عنوان */}
      <div>
        <h1 className="text-xl font-bold">{t.title}</h1>
        <p className={`text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
          {t.subtitle}
        </p>
      </div>

      {/* كارد الإدخال */}
      <div className={`
        p-5 rounded-2xl border space-y-4
        ${isDark 
          ? "bg-slate-800 border-slate-700" 
          : "bg-slate-100 border-slate-200"}
      `}>
        <h2 className="font-semibold text-sm">{t.create}</h2>

        <div className="flex flex-col md:flex-row gap-4">
          
          <input
            type="text"
            placeholder={t.code}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className={`
              flex-1 px-4 py-2 rounded-xl border
              ${isDark 
                ? "bg-slate-900 border-slate-700 text-white" 
                : "bg-white border-slate-300"}
              focus:outline-none focus:ring-2 focus:ring-blue-500
            `}
          />

          <input
            type="number"
            placeholder={t.amount}
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            className={`
              w-full md:w-40 px-4 py-2 rounded-xl border
              ${isDark 
                ? "bg-slate-900 border-slate-700 text-white" 
                : "bg-white border-slate-300"}
              focus:outline-none focus:ring-2 focus:ring-blue-500
            `}
          />

          <button
            onClick={createCode}
            disabled={loading}
            className="px-6 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition shadow"
          >
            {loading ? "..." : t.create}
          </button>
        </div>
      </div>

      {/* فاصل */}
      <div className={`border-t ${isDark ? "border-slate-700" : "border-slate-200"}`} />

      {/* جدول */}
      <div className={`
        rounded-2xl border overflow-hidden
        ${isDark 
          ? "bg-slate-800 border-slate-700" 
          : "bg-slate-100 border-slate-200"}
      `}>
        
        <div className={`px-5 py-4 border-b ${isDark ? "border-slate-700" : "border-slate-200"}`}>
          <h2 className="font-semibold text-sm">{t.title}</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className={isDark ? "bg-slate-900 text-slate-300" : "bg-slate-200 text-slate-600"}>
              <tr>
                <th className="p-3 text-right">{t.code}</th>
                <th className="p-3 text-right">{t.amount}</th>
                <th className="p-3 text-right">{t.status}</th>
                <th className="p-3 text-right">{t.expire}</th>
                <th className="p-3 text-right">{t.action}</th>
              </tr>
            </thead>

            <tbody>
              {codes.map((c) => (
                <tr key={c.code} className="border-t border-slate-300 dark:border-slate-700">
                  <td className="p-3">{c.code}</td>
                  <td className="p-3">{c.amount}</td>
                  <td className="p-3">
                    {c.used ? (
                      <span className="text-red-500">{t.used}</span>
                    ) : (
                      <span className="text-green-500">{t.available}</span>
                    )}
                  </td>
                  <td className="p-3">
                    {new Date(c.expires_at).toLocaleString()}
                  </td>
                  <td className="p-3">
                    <button onClick={() => deleteCode(c.code)} className="text-red-500 hover:underline">
                      {t.delete}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {codes.length === 0 && (
            <div className="text-center py-6 text-slate-400">
              {t.empty}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}