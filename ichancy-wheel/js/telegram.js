/**
 * JADO BOT - Telegram WebApp Integration
 */

class TelegramManager {
    constructor() {
        this.webApp = null;
        this.user = null;
        this.initialized = false;
    }

    async init() {
        try {
            if (window.Telegram && window.Telegram.WebApp) {
                this.webApp = window.Telegram.WebApp;
                this.webApp.ready();
                this.webApp.expand();

                this.user = this.webApp.initDataUnsafe?.user || null;

                this.webApp.setHeaderColor('#0A0A0A');
                this.webApp.setBackgroundColor('#0A0A0A');

                this.initialized = true;
                console.log('Telegram WebApp initialized');
            } else {
                console.log('Telegram WebApp not available - browser mode');
                this.user = {
                    id: 123456789,
                    first_name: 'JADO',
                    username: 'jado_user'
                };
            }

            this.updateUI();
            return true;
        } catch (error) {
            console.error('Telegram init error:', error);
            this.user = { id: 999999, first_name: 'Guest', username: 'guest' };
            return false;
        }
    }

    updateUI() {
        if (!this.user) return;

        const nameEl = document.getElementById('user-name');
        const avatarEl = document.getElementById('user-avatar');

        if (nameEl) {
            nameEl.textContent = this.user.first_name || this.user.username || 'JADO User';
        }

        if (avatarEl) {
            const initial = (this.user.first_name || this.user.username || 'J')[0].toUpperCase();
            avatarEl.textContent = initial;
        }
    }

    getUserId() {
        return this.user ? this.user.id.toString() : 'demo_' + Date.now();
    }

    getUserData() {
        return {
            id: this.getUserId(),
            first_name: this.user?.first_name || 'JADO User',
            username: this.user?.username || 'jado_user'
        };
    }

    sendResultMessage(prize) {
        if (!this.webApp) return;

        const messages = {
            '10000': '🎉 مبروك لقد ربحت 10000',
            '20000': '🎉 مبروك لقد ربحت 20000',
            '50000': '🎉 مبروك لقد ربحت 50000',
            'Telegram Premium': '🎉 مبروك لقد ربحت Telegram Premium',
            'Bonus 5%': '🎉 مبروك لقد ربحت Bonus 5%',
            'إعادة تدوير': '🎉 مبروك حصلت على إعادة تدوير مجانية',
            'حظ أوفر': '😔 حظ أوفر نتمنى لك حظاً أفضل غداً'
        };

        try {
            this.webApp.sendData(JSON.stringify({
                action: 'spin_result',
                prize: prize,
                message: messages[prize] || '🎉 مبروك!',
                user_id: this.getUserId()
            }));
        } catch (e) {
            console.warn('Telegram send failed:', e);
        }
    }

    showAlert(message) {
        if (this.webApp) {
            try { this.webApp.showAlert(message); } catch(e) { alert(message); }
        } else {
            alert(message);
        }
    }

    hapticFeedback(type = 'light') {
        if (this.webApp?.HapticFeedback) {
            try {
                if (type === 'success') this.webApp.HapticFeedback.notificationOccurred('success');
                else if (type === 'error') this.webApp.HapticFeedback.notificationOccurred('error');
                else this.webApp.HapticFeedback.impactOccurred(type);
            } catch(e) {}
        }
    }
}

window.telegramManager = new TelegramManager();
