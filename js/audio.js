/**
 * JADO BOT - Audio System
 * Uses Howler.js with graceful fallback
 */

class AudioManager {
    constructor() {
        this.sounds = {};
        this.muted = false;
        this.initialized = false;
        this.basePath = 'audio/';
        this.available = false;
    }

    async init() {
        if (this.initialized) return;
        if (typeof Howl === 'undefined') {
            console.warn('Howler.js not loaded');
            return;
        }

        const soundFiles = {
            spin: 'spin.mp3',
            ball: 'ball.mp3',
            bounce: 'bounce.mp3',
            win: 'win.mp3',
            lose: 'lose.mp3',
            ambient: 'ambient.mp3'
        };

        for (const [key, file] of Object.entries(soundFiles)) {
            try {
                this.sounds[key] = new Howl({
                    src: [this.basePath + file],
                    preload: true,
                    volume: key === 'ambient' ? 0.3 : 0.8,
                    loop: key === 'ambient',
                    onload: () => { console.log('Loaded:', file); },
                    onloaderror: (id, err) => {
                        console.warn('Audio load error for ' + file + ':', err);
                    }
                });
            } catch (e) {
                console.warn('Failed to create Howl for ' + file);
            }
        }

        this.initialized = true;
        this.available = true;
        console.log('AudioManager initialized');
    }

    play(name, options = {}) {
        if (this.muted || !this.sounds[name]) return null;
        try {
            if (options.volume !== undefined) this.sounds[name].volume(options.volume);
            if (options.rate !== undefined) this.sounds[name].rate(options.rate);
            return this.sounds[name].play();
        } catch (e) {
            console.warn('Play error:', e);
            return null;
        }
    }

    stop(name) {
        if (this.sounds[name]) {
            try { this.sounds[name].stop(); } catch(e) {}
        }
    }

    toggleMute() {
        this.muted = !this.muted;
        if (typeof Howler !== 'undefined') {
            Howler.mute(this.muted);
        }
        return this.muted;
    }

    startAmbient() {
        if (!this.muted && this.sounds.ambient) {
            try {
                this.sounds.ambient.play();
                this.sounds.ambient.fade(0, 0.3, 2000);
            } catch(e) {}
        }
    }

    playSpinSequence() { this.play('spin', { volume: 0.9 }); }
    playBallRoll() { this.play('ball', { volume: 0.7 }); }
    playBounce(intensity = 1) { 
        this.play('bounce', { volume: 0.5 * intensity, rate: 0.8 + Math.random() * 0.4 }); 
    }
    playWin() { this.play('win', { volume: 1.0 }); }
    playLose() { this.play('lose', { volume: 0.8 }); }
}

window.audioManager = new AudioManager();
