/**
 * JADO BOT - Main Application Controller
 * Robust version with 2D Canvas fallback
 */

class JadoRoulette {
    constructor() {
        this.state = {
            initialized: false,
            spinning: false,
            canSpin: true,
            userId: null,
            userData: null,
            balance: 0,
            spinsRemaining: 1,
            soundEnabled: true,
            currentPhase: 'idle',
            use3D: false,
            use2D: true
        };

        this.prizes = [
            { name: '10000', color: '#8B0000', icon: '💵', textColor: '#FFD700' },
            { name: '20000', color: '#2D1B4E', icon: '💵', textColor: '#FFD700' },
            { name: 'حظ أوفر', color: '#8B0000', icon: '🍀', textColor: '#FFD700' },
            { name: 'Telegram Premium', color: '#2D1B4E', icon: '✈️', textColor: '#FFD700' },
            { name: '50000', color: '#8B0000', icon: '💵', textColor: '#FFD700' },
            { name: 'Bonus 5%', color: '#2D1B4E', icon: '🎁', textColor: '#FFD700' },
            { name: 'حظ أوفر', color: '#8B0000', icon: '🍀', textColor: '#FFD700' },
            { name: 'إعادة تدوير', color: '#2D1B4E', icon: '♻️', textColor: '#FFD700' }
        ];

        this.wheelRotation = 0;
        this.ballAngle = 0;
        this.ballRadius = 140;
        this.isAnimating = false;

        console.log('JadoRoulette constructor called');
    }

    async init() {
        try {
            console.log('Starting initialization...');

            // Initialize 2D Canvas wheel first (always works)
            this.init2DWheel();

            // Try to initialize 3D if libraries loaded
            if (typeof THREE !== 'undefined' && typeof gsap !== 'undefined') {
                try {
                    this.init3DWheel();
                    this.state.use3D = true;
                    this.state.use2D = false;
                    console.log('3D wheel initialized');
                } catch (e) {
                    console.warn('3D init failed, using 2D:', e);
                    this.state.use3D = false;
                    this.state.use2D = true;
                }
            } else {
                console.log('3D libraries not available, using 2D');
            }

            // Initialize audio (with fallback)
            if (typeof Howl !== 'undefined') {
                try {
                    await window.audioManager.init();
                    window.audioManager.startAmbient();
                } catch (e) {
                    console.warn('Audio init failed:', e);
                }
            }

            // Initialize Telegram
            try {
                await window.telegramManager.init();
                this.state.userData = window.telegramManager.getUserData();
                this.state.userId = this.state.userData.id;
            } catch (e) {
                console.warn('Telegram init failed, using demo mode:', e);
                this.state.userId = 'demo_' + Date.now();
            }

            // Initialize Supabase (with fallback)
            try {
                await window.supabaseManager.init();
                await this.loadUserData();
            } catch (e) {
                console.warn('Supabase init failed, demo mode:', e);
                this.state.canSpin = true;
                this.state.spinsRemaining = 1;
            }

            // Setup UI
            this.setupEventListeners();
            this.createBackgroundParticles();
            this.updateUI();

            // Show app
            this.showApp();

            this.state.initialized = true;
            console.log('JadoRoulette initialized successfully');

        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('خطأ في التحميل: ' + error.message);
        }
    }

    init2DWheel() {
        console.log('Initializing 2D wheel...');
        const canvas = document.getElementById('wheel-2d');
        if (!canvas) {
            console.error('Canvas not found');
            return;
        }

        // Set canvas size
        const size = Math.min(window.innerWidth * 0.8, 400);
        canvas.width = size;
        canvas.height = size;
        canvas.style.width = size + 'px';
        canvas.style.height = size + 'px';

        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.centerX = size / 2;
        this.centerY = size / 2;
        this.wheelRadius = size / 2 - 20;

        this.draw2DWheel();

        // Show canvas
        canvas.style.display = 'block';

        // Animation loop for 2D
        this.animate2D = () => {
            if (this.state.use2D) {
                this.draw2DWheel();
            }
            requestAnimationFrame(() => this.animate2D());
        };
        this.animate2D();
    }

    draw2DWheel() {
        if (!this.ctx) return;

        const ctx = this.ctx;
        const cx = this.centerX;
        const cy = this.centerY;
        const r = this.wheelRadius;
        const segments = 8;
        const angleStep = (Math.PI * 2) / segments;

        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw segments
        for (let i = 0; i < segments; i++) {
            const startAngle = this.wheelRotation + i * angleStep;
            const endAngle = startAngle + angleStep;
            const prize = this.prizes[i];

            // Segment
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, r, startAngle, endAngle);
            ctx.closePath();
            ctx.fillStyle = prize.color;
            ctx.fill();

            // Gold border
            ctx.strokeStyle = '#FFD700';
            ctx.lineWidth = 3;
            ctx.stroke();

            // Text
            const midAngle = startAngle + angleStep / 2;
            const textR = r * 0.65;
            const tx = cx + Math.cos(midAngle) * textR;
            const ty = cy + Math.sin(midAngle) * textR;

            ctx.save();
            ctx.translate(tx, ty);
            ctx.rotate(midAngle + Math.PI / 2);
            ctx.fillStyle = prize.textColor;
            ctx.font = 'bold 14px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.shadowColor = '#FFD700';
            ctx.shadowBlur = 5;
            ctx.fillText(prize.icon, 0, -10);
            ctx.font = 'bold 11px Arial';
            ctx.fillText(prize.name, 0, 8);
            ctx.restore();
        }

        // Outer gold ring
        ctx.beginPath();
        ctx.arc(cx, cy, r + 5, 0, Math.PI * 2);
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 8;
        ctx.stroke();

        // Inner ring
        ctx.beginPath();
        ctx.arc(cx, cy, r * 0.25, 0, Math.PI * 2);
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 4;
        ctx.stroke();

        // Center hub
        ctx.beginPath();
        ctx.arc(cx, cy, r * 0.22, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a1a';
        ctx.fill();
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 2;
        ctx.stroke();

        // LED dots
        const ledCount = 24;
        for (let i = 0; i < ledCount; i++) {
            const angle = (i / ledCount) * Math.PI * 2 + Date.now() * 0.002;
            const lx = cx + Math.cos(angle) * (r + 12);
            const ly = cy + Math.sin(angle) * (r + 12);

            ctx.beginPath();
            ctx.arc(lx, ly, 3, 0, Math.PI * 2);
            ctx.fillStyle = i % 2 === 0 ? '#FFD700' : '#FFA500';
            ctx.shadowColor = '#FFD700';
            ctx.shadowBlur = 8;
            ctx.fill();
            ctx.shadowBlur = 0;
        }

        // Draw ball if spinning
        if (this.state.spinning || this.ballRadius < 140) {
            const bx = cx + Math.cos(this.ballAngle) * this.ballRadius;
            const by = cy + Math.sin(this.ballAngle) * this.ballRadius;

            ctx.beginPath();
            ctx.arc(bx, by, 8, 0, Math.PI * 2);
            const gradient = ctx.createRadialGradient(bx - 3, by - 3, 0, bx, by, 8);
            gradient.addColorStop(0, '#FFF8DC');
            gradient.addColorStop(0.5, '#FFD700');
            gradient.addColorStop(1, '#B8860B');
            ctx.fillStyle = gradient;
            ctx.shadowColor = '#FFD700';
            ctx.shadowBlur = 10;
            ctx.fill();
            ctx.shadowBlur = 0;
        }
    }

    init3DWheel() {
        if (typeof Wheel3D === 'undefined') {
            console.log('Wheel3D class not available');
            return;
        }
        try {
            window.wheel3D = new Wheel3D();
            const container = document.getElementById('wheel-3d-container');
            if (container) {
                container.style.display = 'block';
                document.getElementById('wheel-2d').style.display = 'none';
            }
        } catch (e) {
            console.error('3D init error:', e);
            throw e;
        }
    }

    setupEventListeners() {
        const spinBtn = document.getElementById('spin-btn');
        if (spinBtn) {
            spinBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.handleSpinClick();
            });
        }

        const soundBtn = document.getElementById('sound-toggle');
        if (soundBtn) {
            soundBtn.addEventListener('click', () => this.toggleSound());
        }

        document.getElementById('deposit-btn')?.addEventListener('click', () => {
            this.closeModal('deposit-modal');
            if (window.telegramManager?.webApp) {
                window.telegramManager.webApp.openTelegramLink('https://t.me/JADO_BOT?start=deposit');
            }
        });

        document.getElementById('win-close')?.addEventListener('click', () => {
            this.closeModal('win-modal');
            this.resetWheel();
        });

        document.getElementById('error-close')?.addEventListener('click', () => {
            this.closeModal('error-modal');
        });

        // Handle resize
        window.addEventListener('resize', () => {
            if (this.state.use2D) {
                this.init2DWheel();
            }
        });
    }

    async handleSpinClick() {
        console.log('Spin clicked, state:', this.state.spinning, this.state.canSpin);

        if (this.state.spinning) {
            console.log('Already spinning');
            return;
        }

        if (!this.state.canSpin) {
            this.showModal('deposit-modal');
            return;
        }

        this.state.spinning = true;
        const spinBtn = document.getElementById('spin-btn');
        if (spinBtn) spinBtn.disabled = true;

        // Get result (from backend or fallback)
        let result;
        try {
            result = await window.supabaseManager?.getSpinResult(this.state.userId);
        } catch (e) {
            console.warn('Backend failed, using local fallback:', e);
            result = this.localSpinResult();
        }

        const targetIndex = this.prizes.findIndex(p => p.name === result);
        console.log('Target:', result, 'index:', targetIndex);

        // Start animation sequence
        await this.spinAnimation(targetIndex >= 0 ? targetIndex : 0, result);
    }

    localSpinResult() {
        // Deterministic fallback (NOT for production)
        const weights = [15, 10, 25, 5, 5, 15, 15, 10];
        const random = Math.random() * 100;
        let cum = 0;
        for (let i = 0; i < weights.length; i++) {
            cum += weights[i];
            if (random <= cum) return this.prizes[i].name;
        }
        return this.prizes[0].name;
    }

    async spinAnimation(targetIndex, result) {
        console.log('Starting spin animation to:', targetIndex);

        // Play sound
        try { window.audioManager?.playSpinSequence(); } catch(e) {}

        // Phase 1: Shake
        this.shakeWheel();
        await this.delay(400);

        // Phase 2: Flash
        this.flashWheel();
        await this.delay(300);

        // Phase 3: Zoom (CSS)
        const wrapper = document.getElementById('wheel-wrapper');
        if (wrapper) wrapper.style.transform = 'scale(1.1)';

        // Calculate final rotation
        const segmentAngle = (Math.PI * 2) / 8;
        const targetAngle = targetIndex * segmentAngle + segmentAngle / 2;
        const spins = 5 + Math.floor(Math.random() * 3);
        const finalRotation = this.wheelRotation + spins * Math.PI * 2 + (Math.PI * 2 - targetAngle);

        // Animate wheel rotation
        const duration = 6000;
        const startRotation = this.wheelRotation;
        const startTime = performance.now();

        // Ball animation
        this.ballRadius = 140;
        let ballSpeed = 0.3;
        let ballAngle = Math.random() * Math.PI * 2;

        return new Promise(resolve => {
            const animate = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Easing (ease-out)
                const easeOut = 1 - Math.pow(1 - progress, 3);

                // Update wheel rotation
                this.wheelRotation = startRotation + (finalRotation - startRotation) * easeOut;

                // Update ball
                if (progress < 0.7) {
                    ballAngle += ballSpeed;
                    ballSpeed *= 0.998;
                } else if (progress < 0.9) {
                    // Ball drops inward
                    this.ballRadius = 140 - (progress - 0.7) * 5 * 70;
                    ballAngle += ballSpeed * 0.5;
                    ballSpeed *= 0.99;
                } else {
                    // Ball settles
                    this.ballRadius = Math.max(75, this.ballRadius);
                    ballAngle = targetAngle + this.wheelRotation;
                }

                this.ballAngle = ballAngle;

                // Play bounce sounds
                if (progress > 0.5 && progress < 0.9 && Math.random() < 0.02) {
                    try { window.audioManager?.playBounce(); } catch(e) {}
                }

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    // Spin complete
                    this.wheelRotation = finalRotation;
                    this.ballRadius = 75;
                    this.ballAngle = targetAngle + finalRotation;
                    this.handleResult(result);
                    resolve();
                }
            };

            requestAnimationFrame(animate);
        });
    }

    shakeWheel() {
        const wrapper = document.getElementById('wheel-wrapper');
        if (!wrapper) return;

        wrapper.style.animation = 'shake 0.5s ease-in-out';
        setTimeout(() => { wrapper.style.animation = ''; }, 500);

        try { window.telegramManager?.hapticFeedback('medium'); } catch(e) {}
    }

    flashWheel() {
        const canvas = document.getElementById('wheel-2d');
        if (canvas) {
            canvas.style.filter = 'brightness(2)';
            setTimeout(() => { canvas.style.filter = ''; }, 200);
            setTimeout(() => { canvas.style.filter = 'brightness(2)'; }, 400);
            setTimeout(() => { canvas.style.filter = ''; }, 600);
        }
    }

    handleResult(result) {
        console.log('Result:', result);

        this.state.spinning = false;
        this.state.spinsRemaining = Math.max(0, this.state.spinsRemaining - 1);
        this.state.canSpin = this.state.spinsRemaining > 0;

        // Update UI
        this.updateUI();

        // Show result modal
        this.showResultModal(result);

        // Send to Telegram
        try { window.telegramManager?.sendResultMessage(result); } catch(e) {}

        // Play sound
        if (result === 'حظ أوفر') {
            try { window.audioManager?.playLose(); } catch(e) {}
        } else {
            try { window.audioManager?.playWin(); } catch(e) {}
        }

        // Haptic
        try {
            if (result !== 'حظ أوفر') {
                window.telegramManager?.hapticFeedback('success');
            } else {
                window.telegramManager?.hapticFeedback('error');
            }
        } catch(e) {}
    }

    showResultModal(result) {
        const modal = document.getElementById('win-modal');
        const icon = document.getElementById('win-icon');
        const title = document.getElementById('win-title');
        const message = document.getElementById('win-message');

        if (!modal) return;

        let iconText = '🎉';
        let titleText = 'مبروك!';
        let messageText = '';

        switch(result) {
            case '10000': messageText = 'لقد ربحت 10000 نقطة!'; break;
            case '20000': messageText = 'لقد ربحت 20000 نقطة!'; break;
            case '50000': messageText = 'لقد ربحت 50000 نقطة!'; break;
            case 'Telegram Premium': messageText = 'لقد ربحت اشتراك Telegram Premium!'; break;
            case 'Bonus 5%': messageText = 'لقد ربحت بونص 5% على إيداعك القادم!'; break;
            case 'إعادة تدوير': messageText = 'حصلت على تدويرة مجانية إضافية!'; break;
            case 'حظ أوفر': 
                iconText = '😔'; 
                titleText = 'حظ أوفر'; 
                messageText = 'نتمنى لك حظاً أفضل غداً!'; 
                break;
        }

        if (icon) icon.textContent = iconText;
        if (title) title.textContent = titleText;
        if (message) message.textContent = messageText;

        modal.classList.remove('hidden');
    }

    resetWheel() {
        const spinBtn = document.getElementById('spin-btn');
        if (spinBtn) spinBtn.disabled = false;

        const wrapper = document.getElementById('wheel-wrapper');
        if (wrapper) wrapper.style.transform = 'scale(1)';

        // Reset ball
        this.ballRadius = 140;
        this.ballAngle = 0;
    }

    toggleSound() {
        const isMuted = window.audioManager?.toggleMute();
        const soundBtn = document.getElementById('sound-toggle');
        const soundIcon = document.getElementById('sound-icon');

        if (isMuted) {
            soundBtn?.classList.add('muted');
            if (soundIcon) soundIcon.textContent = '🔇';
        } else {
            soundBtn?.classList.remove('muted');
            if (soundIcon) soundIcon.textContent = '🔊';
        }
    }

    updateUI() {
        const balanceEl = document.getElementById('user-balance');
        if (balanceEl) balanceEl.textContent = '💰 ' + this.state.balance.toLocaleString();

        const spinsEl = document.getElementById('spins-remaining');
        if (spinsEl) spinsEl.textContent = '🎰 تدويرات: ' + this.state.spinsRemaining;
    }

    async loadUserData() {
        try {
            this.state.balance = await window.supabaseManager.getBalance(this.state.userId) || 0;
            this.state.spinsRemaining = await window.supabaseManager.getTotalSpins(this.state.userId) || 1;
            this.state.canSpin = this.state.spinsRemaining > 0;
        } catch (e) {
            console.warn('Load user data failed:', e);
        }
    }

    showApp() {
        document.getElementById('loading-overlay').style.display = 'none';
        document.getElementById('app').style.display = 'block';
    }

    showError(msg) {
        const errorModal = document.getElementById('error-modal');
        const errorMsg = document.getElementById('error-message');
        if (errorMsg) errorMsg.textContent = msg;
        if (errorModal) errorModal.classList.remove('hidden');
    }

    showModal(id) {
        const modal = document.getElementById(id);
        if (modal) modal.classList.remove('hidden');
    }

    closeModal(id) {
        const modal = document.getElementById(id);
        if (modal) modal.classList.add('hidden');
    }

    createBackgroundParticles() {
        const container = document.getElementById('bg-particles');
        if (!container) return;

        for (let i = 0; i < 20; i++) {
            const p = document.createElement('div');
            p.className = 'particle';
            p.style.left = Math.random() * 100 + '%';
            p.style.animationDuration = (5 + Math.random() * 10) + 's';
            p.style.animationDelay = Math.random() * 5 + 's';
            container.appendChild(p);
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM ready, initializing...');
    window.jadoRoulette = new JadoRoulette();
    window.jadoRoulette.init();
});
