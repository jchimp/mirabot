/**
 * FaceController — SVG face + HAL 9000 state machine.
 *
 * Modes:  "face" (eyes + mouth)  |  "hal" (HAL 9000 eye)
 * States: idle | listening | thinking | speaking
 */
class FaceController {
    constructor() {
        this.state = 'idle';
        this.mode = document.documentElement.getAttribute('data-face') || 'face';
        this.mirror = document.getElementById('mirror');

        // Face elements
        this.mouth = document.getElementById('mouth');
        this.leftEye = document.getElementById('left-eye');
        this.rightEye = document.getElementById('right-eye');
        this.leftPupil = document.getElementById('left-pupil');
        this.rightPupil = document.getElementById('right-pupil');

        // HAL elements
        this.halSvg = document.getElementById('hal');
        this.halLens = document.getElementById('hal-lens');
        this.halCenter = document.getElementById('hal-center');
        this.halHotspot = document.getElementById('hal-hotspot');
        this.halAmbient = document.getElementById('hal-ambient');

        this._blinkTimer = null;
        this._thinkTimer = null;

        this._startBlinking();
    }

    /** Switch between face and HAL mode. */
    setMode(newMode) {
        this.mode = newMode;
        document.documentElement.setAttribute('data-face', newMode);
        localStorage.setItem('mirror-face', newMode);
    }

    /** Transition to a new state. */
    setState(newState) {
        if (this.state === newState) return;
        this._stopThinkingPupils();
        this.mirror.classList.remove(`state-${this.state}`);
        this.mirror.classList.add(`state-${newState}`);
        this.state = newState;

        if (newState === 'thinking') {
            this._startThinkingPupils();
        }
        if (newState === 'idle' || newState === 'listening') {
            this._resetPupils();
            this._resetMouth();
            this._resetHal();
        }
    }

    /**
     * Set amplitude (0–1) — drives mouth OR HAL glow depending on mode.
     * Call in requestAnimationFrame during speaking state.
     */
    setAmplitude(amp) {
        if (this.mode === 'face') {
            this._setMouthAmplitude(amp);
        } else {
            this._setHalAmplitude(amp);
        }
    }

    // ── Face: Mouth ─────────────────────────────

    _setMouthAmplitude(amp) {
        const baseY = 270;
        const controlY = 282 + amp * 45;
        const spread = amp * 6;
        const lx = 165 - spread;
        const rx = 235 + spread;
        this.mouth.setAttribute('d', `M ${lx} ${baseY} Q 200 ${controlY} ${rx} ${baseY}`);
        if (amp > 0.12) {
            this.mouth.setAttribute('fill', `rgba(40, 40, 40, ${amp * 0.7})`);
        } else {
            this.mouth.setAttribute('fill', 'none');
        }
    }

    // ── HAL: Amplitude-driven glow ──────────────

    _setHalAmplitude(amp) {
        // Lens glow intensity: scale the drop-shadow
        const glowBase = 30 + amp * 50;
        const glowOuter = 70 + amp * 80;
        const alphaBase = 0.3 + amp * 0.45;
        const alphaOuter = 0.12 + amp * 0.25;

        this.halSvg.style.filter =
            `drop-shadow(0 0 ${glowBase}px rgba(200, 0, 0, ${alphaBase})) ` +
            `drop-shadow(0 0 ${glowOuter}px rgba(200, 0, 0, ${alphaOuter}))`;

        // Center brightness: scale the bright spots
        const centerScale = 1 + amp * 0.35;
        const centerOpacity = 0.7 + amp * 0.3;
        this.halCenter.setAttribute('r', 12 * centerScale);
        this.halCenter.setAttribute('fill', `rgba(255, 200, 100, ${centerOpacity})`);

        const hotScale = 1 + amp * 0.5;
        const hotOpacity = 0.85 + amp * 0.15;
        this.halHotspot.setAttribute('r', 5 * hotScale);
        this.halHotspot.setAttribute('fill', `rgba(255, 240, 200, ${hotOpacity})`);

        // Ambient glow radius
        const ambientR = 80 + amp * 20;
        const ambientOpacity = 0.06 + amp * 0.12;
        this.halAmbient.setAttribute('r', ambientR);
        this.halAmbient.setAttribute('fill', `rgba(200, 0, 0, ${ambientOpacity})`);
    }

    _resetHal() {
        if (!this.halSvg) return;
        this.halSvg.style.filter = '';
        this.halCenter.setAttribute('r', 12);
        this.halCenter.setAttribute('fill', 'rgba(255, 200, 100, 0.7)');
        this.halHotspot.setAttribute('r', 5);
        this.halHotspot.setAttribute('fill', 'rgba(255, 240, 200, 0.9)');
        this.halAmbient.setAttribute('r', 80);
        this.halAmbient.setAttribute('fill', 'rgba(200, 0, 0, 0.06)');
    }

    // ── Face: Eyes ──────────────────────────────

    _startBlinking() {
        const scheduleBlink = () => {
            const delay = 2500 + Math.random() * 4000;
            this._blinkTimer = setTimeout(() => {
                this._blink();
                scheduleBlink();
            }, delay);
        };
        scheduleBlink();
    }

    _blink() {
        if (this.mode !== 'face') return;
        [this.leftEye, this.rightEye].forEach(eye => {
            eye.classList.add('blinking');
            setTimeout(() => eye.classList.remove('blinking'), 200);
        });
    }

    _startThinkingPupils() {
        let step = 0;
        const positions = [
            { cx: -3, cy: 0 },
            { cx: -2, cy: -2 },
            { cx:  3, cy: 0 },
            { cx:  2, cy: -1 },
            { cx:  0, cy:  0 },
        ];
        this._thinkTimer = setInterval(() => {
            const p = positions[step % positions.length];
            this.leftPupil.setAttribute('cx', 155 + p.cx);
            this.leftPupil.setAttribute('cy', 178 + p.cy);
            this.rightPupil.setAttribute('cx', 245 + p.cx);
            this.rightPupil.setAttribute('cy', 178 + p.cy);
            step++;
        }, 600);
    }

    _stopThinkingPupils() {
        if (this._thinkTimer) {
            clearInterval(this._thinkTimer);
            this._thinkTimer = null;
        }
    }

    _resetPupils() {
        this.leftPupil.setAttribute('cx', 155);
        this.leftPupil.setAttribute('cy', 178);
        this.rightPupil.setAttribute('cx', 245);
        this.rightPupil.setAttribute('cy', 178);
    }

    _resetMouth() {
        this.mouth.setAttribute('d', 'M 165 270 Q 200 285 235 270');
        this.mouth.setAttribute('fill', 'none');
    }

    destroy() {
        clearTimeout(this._blinkTimer);
        this._stopThinkingPupils();
    }
}