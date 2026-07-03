/**
 * Nexus Mobile — UI sound effects (Web Audio API, no external files)
 */
(function () {
    'use strict';

    const DEFAULT_PREFS = {
        master: 0.7,
        muted: false,
        ui: true,
        nav: true,
        progress: true,
        success: true,
        error: true
    };

    let audioCtx = null;

    function getPrefs() {
        try {
            return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem('nexus_audio_prefs') || '{}') };
        } catch (_) {
            return { ...DEFAULT_PREFS };
        }
    }

    function savePrefs(prefs) {
        localStorage.setItem('nexus_audio_prefs', JSON.stringify(prefs));
    }

    function ctx() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') audioCtx.resume().catch(() => {});
        return audioCtx;
    }

    function tone(freq, duration, type, gainVal) {
        const prefs = getPrefs();
        if (prefs.muted) return;
        try {
            const c = ctx();
            const osc = c.createOscillator();
            const gain = c.createGain();
            osc.type = type || 'sine';
            osc.frequency.value = freq;
            gain.gain.value = (gainVal || 0.08) * prefs.master;
            gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);
            osc.connect(gain);
            gain.connect(c.destination);
            osc.start(c.currentTime);
            osc.stop(c.currentTime + duration);
        } catch (_) {}
    }

    const SOUNDS = {
        tap: () => tone(880, 0.04, 'sine', 0.06),
        nav: () => tone(660, 0.05, 'triangle', 0.05),
        success: () => { tone(523, 0.08, 'sine', 0.07); setTimeout(() => tone(784, 0.1, 'sine', 0.07), 70); },
        error: () => tone(220, 0.12, 'square', 0.05),
        progress: () => tone(440, 0.06, 'sine', 0.05),
        complete: () => { tone(392, 0.07, 'sine', 0.06); setTimeout(() => tone(523, 0.09, 'sine', 0.07), 60); setTimeout(() => tone(659, 0.11, 'sine', 0.07), 120); }
    };

    window.NexusAudio = {
        getPrefs,
        savePrefs,
        play(kind) {
            const prefs = getPrefs();
            if (prefs.muted) return;
            const map = { tap: 'ui', nav: 'nav', success: 'success', error: 'error', progress: 'progress', complete: 'progress' };
            const key = map[kind] || 'ui';
            if (prefs[key] === false) return;
            const fn = SOUNDS[kind] || SOUNDS.tap;
            fn();
        },
        initSettingsUI() {
            const prefs = getPrefs();
            const master = document.getElementById('cfg-audio-master');
            const muted = document.getElementById('toggle-audio-muted');
            if (master) master.value = Math.round((prefs.master || 0.7) * 100);
            if (muted) muted.checked = !!prefs.muted;
            ['ui', 'nav', 'progress', 'success', 'error'].forEach(cat => {
                const cb = document.getElementById('toggle-audio-' + cat);
                if (cb) cb.checked = prefs[cat] !== false;
            });
        },
        setMaster(val) {
            const prefs = getPrefs();
            prefs.master = Math.max(0, Math.min(1, Number(val) / 100));
            savePrefs(prefs);
        },
        setMuted(val) {
            const prefs = getPrefs();
            prefs.muted = !!val;
            savePrefs(prefs);
        },
        setCategory(cat, val) {
            const prefs = getPrefs();
            prefs[cat] = !!val;
            savePrefs(prefs);
        },
        testSound() {
            this.play('complete');
        }
    };

    window.setAudioMaster = (v) => window.NexusAudio.setMaster(v);
    window.setAudioMuted = (v) => window.NexusAudio.setMuted(v);
    window.setAudioCategory = (c, v) => window.NexusAudio.setCategory(c, v);
    window.testUiSound = () => window.NexusAudio.testSound();
})();
