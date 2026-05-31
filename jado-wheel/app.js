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

        this.init();
    }

    init() {
        if (this.tg) {
            this.tg.ready();
            this.tg.expand();
            this.user = this.tg.initDataUnsafe?.user;
            this.tg.setHeaderColor('#1a0a2e');
            this.tg.setBackgroundColor('#0a0a0a');
        }

        this.setupLights();
        this.drawWheel();
        this.checkSpinStatus();
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
            // Section angles: each section spans 45°
            // Section 0: centered at 0° (top), spans -22.5° to +22.5°
            const centerAngle = i * sectionAngle - Math.PI / 2;
            const startAngle = centerAngle - sectionAngle / 2;
            const endAngle = centerAngle + sectionAngle / 2;

            // Radial gradient
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

            // Gold divider lines between sections
            ctx.strokeStyle = '#D4AF37';
            ctx.lineWidth = 3;
            ctx.stroke();

            // ===== DRAW LABEL ON WHEEL =====
            // Position text at 65% of radius from center
            const textRadius = radius * 0.65;
            const textX = cx + Math.cos(centerAngle) * textRadius;
            const textY = cy + Math.sin(centerAngle) * textRadius;

            // Draw the label from config.js ON the wheel
            ctx.font = 'bold 28px "Cairo", Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#FFD700';
            ctx.shadowColor = 'rgba(0,0,0,0.7)';
            ctx.shadowBlur = 4;
            ctx.fillText(section.label, textX, textY);
            ctx.shadowBlur = 0;
        });

        // Outer gold ring
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.strokeStyle = '#D4AF37';
        ctx.lineWidth = 7;
        ctx.stroke();

        // Inner circle (behind SPIN button)
        ctx.beginPath();
        ctx.arc(cx, cy, radius * 0.20, 0, Math.PI * 2);
        ctx.fillStyle = '#1a0a2e';
        ctx.fill();
        ctx.strokeStyle = '#D4AF37';
        ctx.lineWidth = 3;
        ctx.stroke();
    }

    checkSpinStatus() {
        const urlParams = new URLSearchParams(window.location.search);
        const canSpin = urlParams.get('can_spin') !== 'false';
        if (!canSpin) {
            this.spinUsed = true;
            this.spinBtn.disabled = true;
        }
    }

    // ===== SPIN - FIXED: Correct landing on exact section =====
    spinWheel() {
        if (this.isSpinning) return;
        if (this.spinUsed) {
            this.showResult({
                icon: '⚠️',
                label: 'تنبيه',
                value: 'لقد استخدمت تدويرتك اليوم! عد غداً بعد الإيداع.',
                isAlert: true
            });
            return;
        }

        this.isSpinning = true;
        this.spinBtn.disabled = true;
        this.spinUsed = true;

        if (this.soundEnabled && this.spinSound) {
            this.spinSound.currentTime = 0;
            this.spinSound.play().catch(() => {});
        }

        // 1. Pick result FIRST (before animation)
        const result = this.calculateResult();
        const targetSection = result.section;
        const targetAngle = targetSection.angle;

        // 2. Calculate exact rotation to land on target section
        // 
        // Pointer is FIXED at top (0°).
        // Wheel rotates CLOCKWISE by R degrees.
        // A section at wheel angle A will appear at screen position: (A + R) mod 360
        // We want: (targetAngle + R) mod 360 = 0  (pointer at top)
        // So: R = (360 - targetAngle) mod 360, plus full rotations for effect
        //
        // Example: target = 20000 (section 1, angle 45°)
        //   R = 360 - 45 = 315° + N*360
        //   After rotation: section at 45° moves to 45+315 = 360° = 0° (top) ✓

        const fullRotations = CONFIG.MIN_SPINS + Math.floor(Math.random() * (CONFIG.MAX_SPINS - CONFIG.MIN_SPINS + 1));
        const adjustment = (360 - targetAngle) % 360;
        const totalRotation = fullRotations * 360 + adjustment;
        const finalRotation = this.currentRotation + totalRotation;

        // 3. Animate
        const duration = CONFIG.SPIN_DURATION;
        const startTime = performance.now();
        const startRot = this.currentRotation;
        let lastSection = -1;

        const animate = (now) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // Ease-out cubic for realistic deceleration
            const ease = 1 - Math.pow(1 - progress, 3);
            const currentAngle = startRot + (finalRotation - startRot) * ease;

            this.wheel.style.transform = 'rotate(' + currentAngle + 'deg)';

            // Tick sound when passing section boundaries
            if (this.soundEnabled && this.tickSound) {
                const secAngle = 360 / CONFIG.SECTIONS.length;
                // Which section is at the pointer now?
                // Pointer sees: (360 - rotation) mod 360
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
                // Verify correct landing
                const finalPointerAngle = (360 - (finalRotation % 360)) % 360;
                const landedIndex = Math.floor(finalPointerAngle / 45);
                console.log('Target:', targetSection.id, 'Landed:', landedIndex, 'Label:', CONFIG.SECTIONS[landedIndex].label);

                this.onSpinComplete(result);
            }
        };

        requestAnimationFrame(animate);
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

        // Show result using the SAME label from config.js
        this.showResult({
            icon: this.getResultIcon(result.section.type),
            label: result.section.label,  // ← FROM CONFIG.JS (same as on wheel)
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
        // Message uses the SAME label from config.js
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
            result_label: result.section.label,  // ← Same label from config.js
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
