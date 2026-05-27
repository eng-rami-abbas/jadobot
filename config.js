// ===== JADO BOT - Wheel Configuration =====
// ✏️ EDIT THE 'label' FIELD FOR EACH SECTION
// These labels appear ON the wheel AND in the result message

const CONFIG = {
    MIN_SPINS: 5,
    MAX_SPINS: 8,
    SPIN_DURATION: 4500,

    // ============================================
    // ✏️ EDIT THESE LABELS - They appear ON the wheel AND in result messages
    // ============================================

    // Wheel has 8 sections. Pointer is FIXED at top (0°).
    // Sections are placed clockwise around the wheel.
    // 
    // Section 0: at 0°   (top, where pointer points when stopped)
    // Section 1: at 45°  (top-right)
    // Section 2: at 90°  (right)
    // Section 3: at 135° (bottom-right)
    // Section 4: at 180° (bottom)
    // Section 5: at 225° (bottom-left)
    // Section 6: at 270° (left)
    // Section 7: at 315° (top-left)

    SECTIONS: [
        { 
            id: 0, 
            angle: 0,           // Position on wheel canvas
            label: '10000',     // ✏️ EDIT: Text shown ON wheel + in result
            type: 'money', 
            value: 10000, 
            color: '#8B0000',   // Red section
            colorDark: '#4a0000'
        },
        { 
            id: 1, 
            angle: 45, 
            label: '20000',     // ✏️ EDIT: Text shown ON wheel + in result
            type: 'money', 
            value: 20000, 
            color: '#1a0a2e',   // Purple section
            colorDark: '#0d0518'
        },
        { 
            id: 2, 
            angle: 90, 
            label: 'حظ أوفر',    // ✏️ EDIT: Text shown ON wheel + in result
            type: 'lucky', 
            value: 0, 
            color: '#8B0000',   // Red section
            colorDark: '#4a0000'
        },
        { 
            id: 3, 
            angle: 135, 
            label: 'تيليجرام بريميوم', // ✏️ EDIT: Text shown ON wheel + in result
            type: 'premium', 
            value: 0, 
            color: '#1a0a2e',   // Purple section
            colorDark: '#0d0518'
        },
        { 
            id: 4, 
            angle: 180, 
            label: 'بونص 5%',     // ✏️ EDIT: Text shown ON wheel + in result
            type: 'bonus', 
            value: 5, 
            color: '#8B0000',   // Red section
            colorDark: '#4a0000'
        },
        { 
            id: 5, 
            angle: 225, 
            label: '50000',       // ✏️ EDIT: Text shown ON wheel + in result
            type: 'money', 
            value: 50000, 
            color: '#1a0a2e',   // Purple section
            colorDark: '#0d0518'
        },
        { 
            id: 6, 
            angle: 270, 
            label: 'حظ أوفر',     // ✏️ EDIT: Text shown ON wheel + in result
            type: 'lucky', 
            value: 0, 
            color: '#8B0000',   // Red section
            colorDark: '#4a0000'
        },
        { 
            id: 7, 
            angle: 315, 
            label: 'إعادة تدوير', // ✏️ EDIT: Text shown ON wheel + in result
            type: 'respins', 
            value: 1, 
            color: '#1a0a2e',   // Purple section
            colorDark: '#0d0518'
        }
    ],

    // ============================================
    // ✏️ EDIT PROBABILITIES (must sum to 1.00)
    // ============================================
    WEIGHTS: [0.20, 0.15, 0.15, 0.05, 0.15, 0.05, 0.15, 0.10]
};
// ===== SUPABASE CONFIGURATION =====
// ⚠️ استخدم المفتاح العام (anon key) وليس مفتاح الخدمة السري!
const SUPABASE_CONFIG = {
    URL: 'https://kpnxtvargeajpxgswdso.supabase.co',  // ضع رابط مشروعك
    ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtwbnh0dmFyZ2VhanB4Z3N3ZHNvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1MTM1NDgsImV4cCI6MjA5MjA4OTU0OH0.nLWI13zA_60KixjgE-ErieCuaSg3D756zRW_FqwOh-g'               // ضع المفتاح العام
};
window.SUPABASE_CONFIG = SUPABASE_CONFIG;
window.CONFIG = CONFIG;
