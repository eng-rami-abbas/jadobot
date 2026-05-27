// ===== JADO BOT - Wheel WebApp =====
// Labels from config.js appear ON the wheel canvas AND in result message

class JadoWheel {
    constructor() {
        this.canvas = document.getElementById('wheel-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.wheel = document.getElementById('wheel');
        this.spinBtn = document.getElementById('spin-btn');
        this.soundBtn = document.getElementById('sound-btn');

        this.currentRotation = 0;
        this.isSpinning = false;
        this.soundEnabled = true;
        this.spinUsed = false;

        this.spinSound = document.getElementById('spin-sound');
        this.winSound = document.getElementById('win-sound');
        this.tickSound = document.getElementById('tick-sound');

        this.tg = window.Telegram?.WebApp;
        this.user = null;

        // Supabase client
        this.supabase = null;
        this.eligibilityChecked = false;
        this.canSpinToday = false;

        this.init();
    }

    async init() {
        if (this.tg) {
            this.tg.ready();
            this.tg.expand();
            this.user = this.tg.initDataUnsafe?.user;
            this.tg.setHeaderColor('#1a0a2e');
            this.tg.setBackgroundColor('#0a0a0a');
        }

        this.setupLights();
        this.drawWheel();
        this.spinBtn.disabled = true; // معطّل حتى التحقق

        // تهيئة Supabase والتحقق من الأهلية
        await this.initSupabase();
        await this.checkEligibility();
    }

    // تهيئة Supabase
    async initSupabase() {
        if (!window.SUPABASE_CONFIG || !window.SUPABASE_CONFIG.URL || window.SUPABASE_CONFIG.URL === 'https://your-project-id.supabase.co') {
            console.warn('Supabase config not set. Skipping eligibility check.');
            return;
        }
        try {
            const { createClient } = supabase; // من مكتبة Supabase المضافة
            this.supabase = createClient(window.SUPABASE_CONFIG.URL, window.SUPABASE_CONFIG.ANON_KEY);
            console.log('Supabase initialized');
        } catch (e) {
            console.error('Supabase init error:', e);
        }
    }

    // التحقق من شرط الإيداع وعدم وجود تدويرة اليوم
    async checkEligibility() {
        if (!this.supabase || !this.user?.id) {
            // لا يمكن التحقق، نسمح بالتدوير (لأغراض التطوير)
            this.enableSpin();
            return;
        }

        try {
            const userId = this.user.id.toString();

            // 1. التحقق من وجود إيداع واحد على الأقل للمستخدم
            const { data: deposit, error: depError } = await this.supabase
                .from('deposits')
                .select('id')
                .eq('user_id', userId)
                .limit(1);

            if (depError) throw depError;
            if (!deposit || deposit.length === 0) {
                // لا يوجد إيداع
                this.spinBtn.disabled = true;
                this.showSpinMessage('يجب عليك الإيداع أولاً لاستخدام العجلة.');
                return;
            }

            // 2. التحقق من عدم وجود تدويرة مسجلة اليوم
            const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
            const { data: todaySpin, error: spinError } = await this.supabase
                .from('spins')
                .select('id')
                .eq('user_id', userId)
                .eq('spin_date', today)
                .limit(1);

            if (spinError) throw spinError;
            if (todaySpin && todaySpin.length > 0) {
                this.spinUsed = true;
                this.spinBtn.disabled = true;
                this.showSpinMessage('لقد استخدمت تدويرتك اليوم. عد غداً!');
                return;
            }

            // كل الشروط محققة
            this.spinUsed = false;
            this.canSpinToday = true;
            this.enableSpin();

        } catch (error) {
            console.error('Eligibility check failed:', error);
            // في حالة الخطأ نسمح بالتدوير (للتجربة)
            this.enableSpin();
        }
    }

    enableSpin() {
        this.spinBtn.disabled = false;
        this.eligibilityChecked = true;
    }

    showSpinMessage(msg) {
        // عرض رسالة للمستخدم (مؤقت)
        if (this.tg) {
            this.tg.showAlert(msg);
        } else {
            alert(msg);
        }
    }

    setupLights() {
        const container = document.getElementById('lights');
        const count = 24;
        const radius = 155;

        for (let i = 0; i < count; i++) {
            const angle = (i / count) * Math.PI * 2 - Math.PI / 2;
            const x = 50 + (radius / 320 * 100) * Math.cos(angle);
            const y = 50 + (radius / 320 * 100) * Math.sin(angle);

            const bulb = document.createElement('div');
            bulb.className = 'light-bulb';
            bulb.style.left = x + '%';
            bulb.style.top = y + '%';
            bulb.style.transform = 'translate(-50%, -50%)';
            bulb.style.animationDelay = (i * 0.08) + 's';
            container.appendChild(bulb);
        }
    }

    // ===== DRAW WHEEL - Labels from config.js appear ON the wheel =====
    drawWheel() {
        const ctx = this.ctx;
        const size = 600;
        const cx = size / 2;
        const cy = size / 2;
        const radius = size / 2 - 8;
        const sections = CONFIG.SECTIONS;
        const sectionAngle = (Math.PI * 2) / sections.length; // 45° = π/4

        ctx.clearRect(0, 0, size, size);

        sections.forEach((section, i) => {
            const centerAngle = i * sectionAngle - Math.PI / 2;
            const startAngle = centerAngle - sectionAngle / 2;
            const endAngle = centerAngle + sectionAngle / 2;

            const grad = ctx.createRadialGradient(cx, cy, radius * 0.15, cx, cy, radius);
            grad.addColorStop(0, section.colorDark);
            grad.addColorStop(0.6, section.color);
            grad.addColorStop(1, section.colorDark);

            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, radius, startAngle, endAngle);
            ctx.closePath();
            ctx.fillStyle = grad;
            ctx.fill();

            ctx.strokeStyle = '#D4AF37';
            ctx.lineWidth = 3;
            ctx.stroke();

            const textRadius = radius * 0.65;
            const textX = cx + Math.cos(centerAngle) * textRadius;
            const textY = cy + Math.sin(centerAngle) * textRadius;

            ctx.font = 'bold 28px "Cairo", Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#FFD700';
            ctx.shadowColor = 'rgba(0,0,0,0.7)';
            ctx.shadowBlur = 4;
            ctx.fillText(section.label, textX, textY);
            ctx.shadowBlur = 0;
        });

        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.strokeStyle = '#D4AF37';
        ctx.lineWidth = 7;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(cx, cy, radius * 0.20, 0, Math.PI * 2);
        ctx.fillStyle = '#1a0a2e';
        ctx.fill();
        ctx.strokeStyle = '#D4AF37';
        ctx.lineWidth = 3;
        ctx.stroke();
    }

    // ===== SPIN =====
    async spinWheel() {
        if (this.isSpinning) return;
        if (!this.eligibilityChecked || !this.canSpinToday) {
            this.showResult({
                icon: '⚠️',
                label: 'تنبيه',
                value: 'لا يمكنك التدوير الآن. تأكد من الإيداع ومن أنك لم تستخدم تدويرتك اليوم.',
                isAlert: true
            });
            return;
        }

        // تسجيل التدويرة في قاعدة البيانات قبل بدء الدوران
        const spinRegistered = await this.registerSpin();
        if (!spinRegistered) {
            this.showResult({
                icon: '⚠️',
                label: 'خطأ',
                value: 'حدث خطأ أثناء محاولة تسجيل التدويرة. حاول مجدداً.',
                isAlert: true
            });
            return;
        }

        this.isSpinning = true;
        this.spinBtn.disabled = true;
        this.spinUsed = true;
        this.canSpinToday = false; // منع الضغط مرة أخرى

        if (this.soundEnabled && this.spinSound) {
            this.spinSound.currentTime = 0;
            this.spinSound.play().catch(() => {});
        }

        const result = this.calculateResult();
        const targetSection = result.section;
        const targetAngle = targetSection.angle;

        const fullRotations = CONFIG.MIN_SPINS + Math.floor(Math.random() * (CONFIG.MAX_SPINS - CONFIG.MIN_SPINS + 1));
        const adjustment = (360 - targetAngle) % 360;
        const totalRotation = fullRotations * 360 + adjustment;
        const finalRotation = this.currentRotation + totalRotation;

        const duration = CONFIG.SPIN_DURATION;
        const startTime = performance.now();
        const startRot = this.currentRotation;
        let lastSection = -1;

        const animate = (now) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const ease = 1 - Math.pow(1 - progress, 3);
            const currentAngle = startRot + (finalRotation - startRot) * ease;

            this.wheel.style.transform = 'rotate(' + currentAngle + 'deg)';

            if (this.soundEnabled && this.tickSound) {
                const secAngle = 360 / CONFIG.SECTIONS.length;
                const pointerAngle = (360 - (currentAngle % 360)) % 360;
                const currentSec = Math.floor(pointerAngle / secAngle);
                if (currentSec !== lastSection) {
                    this.tickSound.currentTime = 0;
                    this.tickSound.play().catch(() => {});
                    lastSection = currentSec;
                }
            }

            this.currentRotation = currentAngle;

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                const finalPointerAngle = (360 - (finalRotation % 360)) % 360;
                const landedIndex = Math.floor(finalPointerAngle / 45);
                console.log('Target:', targetSection.id, 'Landed:', landedIndex, 'Label:', CONFIG.SECTIONS[landedIndex].label);

                this.onSpinComplete(result);
            }
        };

        requestAnimationFrame(animate);
    }

    // تسجيل التدويرة في Supabase
    async registerSpin() {
        if (!this.supabase || !this.user?.id) return true; // إذا لم يتوفر Supabase، نسمح (للتطوير)

        try {
            const userId = this.user.id.toString();
            const today = new Date().toISOString().split('T')[0];

            const { error } = await this.supabase
                .from('spins')
                .insert([
                    {
                        user_id: userId,
                        spin_date: today,
                        created_at: new Date().toISOString()
                    }
                ]);

            if (error) {
                console.error('Spin registration error:', error);
                // ربما الخطأ بسبب انتهاك قيد التفرد (موجود بالفعل)
                if (error.code === '23505') { // unique violation
                    this.spinUsed = true;
                    this.canSpinToday = false;
                    this.spinBtn.disabled = true;
                    this.showSpinMessage('لقد استخدمت تدويرتك اليوم مسبقاً.');
                }
                return false;
            }
            return true;
        } catch (e) {
            console.error('Register spin failed:', e);
            return false;
        }
    }

    calculateResult() {
        const weights = CONFIG.WEIGHTS;
        const random = Math.random();
        let cum = 0;
        let idx = 0;

        for (let i = 0; i < weights.length; i++) {
            cum += weights[i];
            if (random <= cum) {
                idx = i;
                break;
            }
        }

        return {
            section: CONFIG.SECTIONS[idx],
            index: idx
        };
    }

    onSpinComplete(result) {
        this.isSpinning = false;

        if (this.spinSound) {
            this.spinSound.pause();
            this.spinSound.currentTime = 0;
        }

        if (this.soundEnabled && this.winSound) {
            this.winSound.currentTime = 0;
            this.winSound.play().catch(() => {});
        }

        this.showResult({
            icon: this.getResultIcon(result.section.type),
            label: result.section.label,
            value: this.getResultDescription(result.section),
            isAlert: false
        });

        this.sendToBot(result);

        if (result.section.type === 'money' && result.section.value >= 20000) {
            this.createConfetti();
        }
    }

    getResultIcon(type) {
        const icons = {
            money: '💰',
            bonus: '🎁',
            respins: '♻️',
            lucky: '🍀',
            premium: '✈️'
        };
        return icons[type] || '🎯';
    }

    getResultDescription(section) {
        switch (section.type) {
            case 'money': return 'مبروك! ربحت ' + section.label + '!';
            case 'bonus': return 'مبروك! ' + section.label + ' على إيداعك القادم!';
            case 'respins': return 'مبروك! ' + section.label + '!';
            case 'lucky': return 'مبروك! ' + section.label + '!';
            case 'premium': return 'مبروك! ' + section.label + '!';
            default: return section.label;
        }
    }

    showResult(data) {
        const panel = document.getElementById('result-panel');
        document.getElementById('result-icon').textContent = data.icon;
        document.getElementById('result-text').textContent = data.label;
        document.getElementById('result-value').textContent = data.value;
        panel.classList.remove('hidden');
    }

    closeResult() {
        document.getElementById('result-panel').classList.add('hidden');
    }

    sendToBot(result) {
        if (!this.tg) return;

        const data = {
            action: 'wheel_spin_complete',
            result_type: result.section.type,
            result_label: result.section.label,
            result_value: result.section.value,
            user_id: this.user?.id,
            username: this.user?.username,
            timestamp: new Date().toISOString()
        };

        this.tg.sendData(JSON.stringify(data));

        setTimeout(() => {
            this.tg.showConfirm('تم تسجيل النتيجة! اضغط موافق للعودة للبوت.', (confirmed) => {
                if (confirmed) this.tg.close();
            });
        }, 2000);
    }

    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        this.soundBtn.classList.toggle('muted', !this.soundEnabled);
        if (!this.soundEnabled) {
            this.spinSound?.pause();
            this.winSound?.pause();
            this.tickSound?.pause();
        }
    }

    createConfetti() {
        const container = document.createElement('div');
        container.className = 'confetti-container';
        document.body.appendChild(container);

        const colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#FF1744'];

        for (let i = 0; i < 60; i++) {
            const conf = document.createElement('div');
            conf.className = 'confetti';
            conf.style.left = Math.random() * 100 + '%';
            conf.style.background = colors[Math.floor(Math.random() * colors.length)];
            conf.style.animationDelay = Math.random() * 1.5 + 's';
            conf.style.width = (6 + Math.random() * 8) + 'px';
            conf.style.height = (6 + Math.random() * 8) + 'px';
            conf.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
            container.appendChild(conf);
        }

        setTimeout(() => container.remove(), 5000);
    }
}

// ===== Global functions =====
let wheelApp;
function toggleSound() { wheelApp.toggleSound(); }
function spinWheel() { wheelApp.spinWheel(); }
function closeResult() { wheelApp.closeResult(); }

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    wheelApp = new JadoWheel();
});
