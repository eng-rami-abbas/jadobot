/**
 * JADO BOT - Main Application Controller
 * Orchestrates all components for the premium roulette experience
 */

class JadoRoulette {
    constructor() {
        this.state = {
            initialized: false,
            spinning: false,
            canSpin: false,
            userId: null,
            userData: null,
            balance: 0,
            spinsRemaining: 0,
            soundEnabled: true,
            currentPhase: 'idle' // idle, cinematic, spinning, settling, result
        };

        this.prizes = [
            '10000', '20000', 'حظ أوفر', 'Telegram Premium',
            '50000', 'Bonus 5%', 'حظ أوفر', 'إعادة تدوير'
        ];

        this.init();
    }

    async init() {
        try {
            // Initialize audio
            await window.audioManager.init();

            // Initialize Telegram
            await window.telegramManager.init();
            this.state.userData = window.telegramManager.getUserData();
            this.state.userId = this.state.userData.id;

            // Initialize Supabase
            await window.supabaseManager.init();

            // Initialize 3D Wheel
            window.wheel3D = new Wheel3D();

            // Setup event listeners
            this.setupEventListeners();

            // Setup physics callbacks
            this.setupPhysicsCallbacks();

            // Create background particles
            this.createBackgroundParticles();

            // Load user data
            await this.loadUserData();

            // Start ambient sound
            window.audioManager.startAmbient();

            // Hide loading
            this.hideLoading();

            this.state.initialized = true;
            console.log('JadoRoulette initialized successfully');

        } catch (error) {
            console.error('Initialization error:', error);
            this.showMessage('خطأ في التحميل، يرجى المحاولة مرة أخرى');
        }
    }

    setupEventListeners() {
        // Spin button
        const spinBtn = document.getElementById('spin-btn');
        spinBtn.addEventListener('click', () => this.handleSpinClick());

        // Sound toggle
        const soundBtn = document.getElementById('sound-toggle');
        soundBtn.addEventListener('click', () => this.toggleSound());

        // Modal buttons
        document.getElementById('deposit-btn')?.addEventListener('click', () => {
            this.closeModal('deposit-modal');
            // Open deposit link
            if (window.telegramManager.webApp) {
                window.telegramManager.webApp.openTelegramLink('https://t.me/JADO_BOT?start=deposit');
            }
        });

        document.getElementById('win-close')?.addEventListener('click', () => {
            this.closeModal('win-modal');
            this.resetWheel();
        });
    }

    setupPhysicsCallbacks() {
        window.roulettePhysics.on('spinStart', (data) => {
            console.log('Spin started, target:', data.targetPocket);
        });

        window.roulettePhysics.on('bounce', (data) => {
            window.audioManager.playBounce(data.intensity);
            window.telegramManager.hapticFeedback('light');
        });

        window.roulettePhysics.on('ballUpdate', (data) => {
            if (window.wheel3D) {
                window.wheel3D.updateBallPosition(data.angle, data.radius);
            }
        });

        window.roulettePhysics.on('settled', (data) => {
            this.handleBallSettled(data.pocket);
        });
    }

    async loadUserData() {
        try {
            // Get balance
            this.state.balance = await window.supabaseManager.getBalance(this.state.userId);
            this.updateBalanceDisplay();

            // Check deposit status
            const hasDeposit = await window.supabaseManager.hasDeposit(this.state.userId);

            if (!hasDeposit) {
                this.state.canSpin = false;
                this.showModal('deposit-modal');
                return;
            }

            // Get remaining spins
            this.state.spinsRemaining = await window.supabaseManager.getTotalSpins(this.state.userId);
            this.updateSpinsDisplay();

            this.state.canSpin = this.state.spinsRemaining > 0;

        } catch (error) {
            console.error('Load user data error:', error);
            // Demo mode
            this.state.canSpin = true;
            this.state.spinsRemaining = 1;
            this.updateSpinsDisplay();
        }
    }

    async handleSpinClick() {
        if (this.state.spinning || !this.state.canSpin) {
            if (!this.state.canSpin) {
                this.showModal('deposit-modal');
            }
            return;
        }

        this.state.spinning = true;
        this.state.currentPhase = 'cinematic';

        const spinBtn = document.getElementById('spin-btn');
        spinBtn.disabled = true;

        // Get result from backend (SECURE)
        const result = await window.supabaseManager.getSpinResult(this.state.userId);
        const targetIndex = this.prizes.indexOf(result);

        // Start cinematic sequence
        await this.playCinematicSequence(targetIndex, result);
    }

    async playCinematicSequence(targetIndex, result) {
        // Phase 1: Shake
        window.telegramManager.hapticFeedback('medium');
        window.wheel3D.shake();
        window.audioManager.play('spin', { volume: 0.3 });
        await this.delay(500);

        // Phase 2: Gold flash
        window.wheel3D.flashGold();
        await this.delay(300);

        // Phase 3: Camera zoom
        window.wheel3D.zoomCamera(0.7);
        await this.delay(800);

        // Phase 4: Wheel tilts to horizontal
        await window.wheel3D.animateToHorizontal();

        // Phase 5: Button morphs to ball
        await this.morphButtonToBall();

        // Start actual spin
        this.state.currentPhase = 'spinning';
        await this.startSpin(targetIndex, result);
    }

    async morphButtonToBall() {
        const spinBtn = document.getElementById('spin-btn');
        const ballContainer = document.getElementById('ball-container');

        // Hide button with scale animation
        gsap.to(spinBtn, {
            scale: 0,
            opacity: 0,
            duration: 0.5,
            ease: 'back.in(2)',
            onComplete: () => {
                spinBtn.style.display = 'none';
                ballContainer.style.display = 'block';
                gsap.fromTo(ballContainer, 
                    { scale: 0, opacity: 0 },
                    { scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(2)' }
                );
            }
        });
    }

    async startSpin(targetIndex, result) {
        // Record the spin
        await window.supabaseManager.recordSpin(this.state.userId);

        // Play spin sound
        window.audioManager.playSpinSequence();

        // Calculate target angle for the segment
        const segmentAngle = (Math.PI * 2) / 8;
        const targetAngle = targetIndex * segmentAngle + segmentAngle / 2;

        // Start physics simulation
        window.roulettePhysics.startSpin(targetIndex, 0.1, 0.6);

        // Sync Three.js wheel with physics
        this.syncWheelWithPhysics();

        // Wait for physics to settle
        await this.waitForSettle();

        // Handle result
        await this.handleResult(result);
    }

    syncWheelWithPhysics() {
        const sync = () => {
            if (window.roulettePhysics.running && window.wheel3D) {
                const wheelAngle = window.roulettePhysics.getWheelAngle();
                window.wheel3D.wheelGroup.rotation.z = wheelAngle;
                requestAnimationFrame(sync);
            }
        };
        sync();
    }

    waitForSettle() {
        return new Promise(resolve => {
            const check = () => {
                if (!window.roulettePhysics.running) {
                    resolve();
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    }

    async handleBallSettled(pocketIndex) {
        window.audioManager.stop('ball');
        window.telegramManager.hapticFeedback('heavy');
    }

    async handleResult(result) {
        this.state.currentPhase = 'result';

        // Record result in database
        await window.supabaseManager.recordResult(this.state.userId, result);

        // Update balance display
        this.state.balance = await window.supabaseManager.getBalance(this.state.userId);
        this.updateBalanceDisplay();

        // Update spins
        this.state.spinsRemaining = await window.supabaseManager.getTotalSpins(this.state.userId);
        this.updateSpinsDisplay();
        this.state.canSpin = this.state.spinsRemaining > 0;

        // Show result
        this.showResultModal(result);

        // Send to Telegram
        window.telegramManager.sendResultMessage(result);

        // Play sound
        if (result === 'حظ أوفر') {
            window.audioManager.playLose();
        } else {
            window.audioManager.playWin();
        }

        // Haptic feedback
        if (result !== 'حظ أوفر') {
            window.telegramManager.hapticFeedback('success');
        } else {
            window.telegramManager.hapticFeedback('error');
        }
    }

    showResultModal(result) {
        const modal = document.getElementById('win-modal');
        const icon = document.getElementById('win-icon');
        const title = document.getElementById('win-title');
        const message = document.getElementById('win-message');

        let iconText = '🎉';
        let titleText = 'مبروك!';
        let messageText = '';

        switch(result) {
            case '10000':
                messageText = 'لقد ربحت 10000 نقطة!';
                break;
            case '20000':
                messageText = 'لقد ربحت 20000 نقطة!';
                break;
            case '50000':
                messageText = 'لقد ربحت 50000 نقطة!';
                break;
            case 'Telegram Premium':
                messageText = 'لقد ربحت اشتراك Telegram Premium!';
                break;
            case 'Bonus 5%':
                messageText = 'لقد ربحت بونص 5% على إيداعك القادم!';
                break;
            case 'إعادة تدوير':
                messageText = 'حصلت على تدويرة مجانية إضافية!';
                break;
            case 'حظ أوفر':
                iconText = '😔';
                titleText = 'حظ أوفر';
                messageText = 'نتمنى لك حظاً أفضل غداً!';
                break;
        }

        icon.textContent = iconText;
        title.textContent = titleText;
        message.textContent = messageText;

        modal.classList.remove('hidden');
    }

    async resetWheel() {
        this.state.currentPhase = 'idle';
        this.state.spinning = false;

        // Reset physics
        window.roulettePhysics.reset();

        // Animate back to vertical
        await window.wheel3D.animateToVertical();

        // Reset camera
        window.wheel3D.zoomCamera(1, 1);

        // Show button, hide ball
        const spinBtn = document.getElementById('spin-btn');
        const ballContainer = document.getElementById('ball-container');

        ballContainer.style.display = 'none';
        spinBtn.style.display = 'block';
        spinBtn.disabled = false;

        gsap.fromTo(spinBtn, 
            { scale: 0, opacity: 0 },
            { scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(2)' }
        );

        // Reload user data
        await this.loadUserData();
    }

    toggleSound() {
        const isMuted = window.audioManager.toggleMute();
        const soundBtn = document.getElementById('sound-toggle');
        const soundIcon = document.getElementById('sound-icon');

        if (isMuted) {
            soundBtn.classList.add('muted');
            soundIcon.textContent = '🔇';
        } else {
            soundBtn.classList.remove('muted');
            soundIcon.textContent = '🔊';
            window.audioManager.startAmbient();
        }
    }

    updateBalanceDisplay() {
        const balanceEl = document.getElementById('user-balance');
        if (balanceEl) {
            balanceEl.textContent = '💰 ' + this.state.balance.toLocaleString();
        }
    }

    updateSpinsDisplay() {
        const spinsEl = document.getElementById('spins-remaining');
        if (spinsEl) {
            spinsEl.textContent = '🎰 تدويرات: ' + this.state.spinsRemaining;
        }
    }

    showMessage(text) {
        const messageBox = document.getElementById('message-box');
        const messageText = document.getElementById('message-text');

        messageText.textContent = text;
        messageBox.classList.remove('hidden');

        setTimeout(() => {
            messageBox.classList.add('hidden');
        }, 3000);
    }

    showModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    closeModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    hideLoading() {
        const loading = document.getElementById('loading-overlay');
        if (loading) {
            loading.classList.add('hidden');
            setTimeout(() => {
                loading.style.display = 'none';
            }, 500);
        }
    }

    createBackgroundParticles() {
        const container = document.getElementById('bg-particles');
        const particleCount = 30;

        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDuration = (5 + Math.random() * 10) + 's';
            particle.style.animationDelay = Math.random() * 5 + 's';
            particle.style.width = (2 + Math.random() * 4) + 'px';
            particle.style.height = particle.style.width;
            container.appendChild(particle);
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.jadoRoulette = new JadoRoulette();
});
