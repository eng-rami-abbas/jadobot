/**
 * JADO BOT - Audio System
 * Uses Howler.js for premium casino sound effects
 */

class AudioManager {
    constructor() {
        this.sounds = {};
        this.muted = false;
        this.initialized = false;
        this.basePath = 'audio/';
    }

    async init() {
        if (this.initialized) return;

        // Define all sound files
        const soundFiles = {
            spin: 'spin.mp3',
            ball: 'ball.mp3',
            bounce: 'bounce.mp3',
            win: 'win.mp3',
            lose: 'lose.mp3',
            ambient: 'ambient.mp3'
        };

        // Initialize Howl objects
        for (const [key, file] of Object.entries(soundFiles)) {
            this.sounds[key] = new Howl({
                src: [this.basePath + file],
                preload: true,
                volume: key === 'ambient' ? 0.3 : 0.8,
                loop: key === 'ambient',
                onloaderror: (id, err) => {
                    console.warn(`Audio load error for ${file}:`, err);
                }
            });
        }

        this.initialized = true;
        console.log('AudioManager initialized');
    }

    play(name, options = {}) {
        if (this.muted || !this.sounds[name]) return null;

        const sound = this.sounds[name];

        if (options.volume !== undefined) {
            sound.volume(options.volume);
        }

        if (options.rate !== undefined) {
            sound.rate(options.rate);
        }

        return sound.play();
    }

    stop(name) {
        if (this.sounds[name]) {
            this.sounds[name].stop();
        }
    }

    fade(name, from, to, duration) {
        if (this.sounds[name]) {
            this.sounds[name].fade(from, to, duration);
        }
    }

    toggleMute() {
        this.muted = !this.muted;
        Howler.mute(this.muted);
        return this.muted;
    }

    isMuted() {
        return this.muted;
    }

    // Play ambient background
    startAmbient() {
        if (!this.muted && this.sounds.ambient) {
            this.sounds.ambient.play();
            this.sounds.ambient.fade(0, 0.3, 2000);
        }
    }

    stopAmbient() {
        if (this.sounds.ambient) {
            this.sounds.ambient.fade(0.3, 0, 1000);
            setTimeout(() => this.sounds.ambient.stop(), 1000);
        }
    }

    // Play spin sequence
    playSpinSequence() {
        this.play('spin', { volume: 0.9 });
    }

    // Play ball rolling
    playBallRoll() {
        this.play('ball', { volume: 0.7, rate: 1.2 });
    }

    // Play bounce effect
    playBounce(intensity = 1) {
        this.play('bounce', { 
            volume: 0.5 * intensity,
            rate: 0.8 + Math.random() * 0.4
        });
    }

    // Play win sound
    playWin() {
        this.stopAmbient();
        this.play('win', { volume: 1.0 });
        setTimeout(() => this.startAmbient(), 3000);
    }

    // Play lose sound
    playLose() {
        this.stopAmbient();
        this.play('lose', { volume: 0.8 });
        setTimeout(() => this.startAmbient(), 2000);
    }
}

// Global instance
window.audioManager = new AudioManager();
