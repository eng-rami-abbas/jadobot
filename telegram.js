/**
 * JADO BOT - Telegram WebApp Integration
 * Handles Telegram WebApp SDK and user data
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

                // Get user data
                this.user = this.webApp.initDataUnsafe?.user || null;

                // Set theme
                this.webApp.setHeaderColor('#0A0A0A');
                this.webApp.setBackgroundColor('#0A0A0A');

                this.initialized = true;
                console.log('TelegramManager initialized, user:', this.user);
            } else {
                console.warn('Telegram WebApp not available - running in browser mode');
                // Demo user for testing
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
            if (this.user.photo_url) {
                avatarEl.style.backgroundImage = `url(${this.user.photo_url})`;
                avatarEl.style.backgroundSize = 'cover';
            } else {
                const initial = (this.user.first_name || this.user.username || 'J')[0].toUpperCase();
                avatarEl.textContent = initial;
            }
        }
    }

    getUserId() {
        return this.user ? this.user.id.toString() : 'demo_user';
    }

    getUserData() {
        return {
            id: this.getUserId(),
            first_name: this.user?.first_name || 'JADO User',
            username: this.user?.username || 'jado_user'
        };
    }

    // Send result message to bot
    sendResultMessage(prize) {
        if (!this.webApp) return;

        let message = '';

        switch(prize) {
            case '10000':
                message = '🎉 مبروك لقد ربحت 10000';
                break;
            case '20000':
                message = '🎉 مبروك لقد ربحت 20000';
                break;
            case '50000':
                message = '🎉 مبروك لقد ربحت 50000';
                break;
            case 'Telegram Premium':
                message = '🎉 مبروك لقد ربحت Telegram Premium';
                break;
            case 'Bonus 5%':
                message = '🎉 مبروك لقد ربحت Bonus 5%';
                break;
            case 'إعادة تدوير':
                message = '🎉 مبروك حصلت على إعادة تدوير مجانية';
                break;
            case 'حظ أوفر':
                message = '😔 حظ أوفر نتمنى لك حظاً أفضل غداً';
                break;
            default:
                message = `🎉 مبروك لقد ربحت ${prize}`;
        }

        // Send data to bot
        this.webApp.sendData(JSON.stringify({
            action: 'spin_result',
            prize: prize,
            message: message,
            user_id: this.getUserId()
        }));
    }

    // Show alert
    showAlert(message) {
        if (this.webApp) {
            this.webApp.showAlert(message);
        } else {
            alert(message);
        }
    }

    // Show confirm
    showConfirm(message, callback) {
        if (this.webApp) {
            this.webApp.showConfirm(message, callback);
        } else {
            const result = confirm(message);
            callback(result);
        }
    }

    // Haptic feedback
    hapticFeedback(type = 'light') {
        if (this.webApp && this.webApp.HapticFeedback) {
            switch(type) {
                case 'light':
                    this.webApp.HapticFeedback.impactOccurred('light');
                    break;
                case 'medium':
                    this.webApp.HapticFeedback.impactOccurred('medium');
                    break;
                case 'heavy':
                    this.webApp.HapticFeedback.impactOccurred('heavy');
                    break;
                case 'success':
                    this.webApp.HapticFeedback.notificationOccurred('success');
                    break;
                case 'error':
                    this.webApp.HapticFeedback.notificationOccurred('error');
                    break;
            }
        }
    }

    // Close WebApp
    close() {
        if (this.webApp) {
            this.webApp.close();
        }
    }
}

// Global instance
window.telegramManager = new TelegramManager();
