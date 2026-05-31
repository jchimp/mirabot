/**
 * AudioManager — handles mic capture and audio playback with analyser.
 *
 * Recording:  start() / stop() → returns Blob
 * Playback:   play(base64Wav)  → connects to AnalyserNode for mouth sync
 */
class AudioManager {
    constructor() {
        this.mediaRecorder = null;
        this.chunks = [];
        this.stream = null;
        this.audioContext = null;
        this.analyser = null;
        this.isPlaying = false;
    }

    /** Request mic permission and prepare AudioContext. */
    async init() {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.7;
        console.log('✅ Mic access granted');
    }

    /** Start recording. */
    start() {
        this.chunks = [];

        // Try formats in order of preference
        const formats = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4',
            '',
        ];

        let mimeType = '';
        for (const fmt of formats) {
            if (fmt === '' || MediaRecorder.isTypeSupported(fmt)) {
                mimeType = fmt;
                break;
            }
        }

        console.log('MediaRecorder using:', mimeType || '(browser default)');

        const options = mimeType ? { mimeType } : {};

        try {
            this.mediaRecorder = new MediaRecorder(this.stream, options);
        } catch (e) {
            console.warn('MediaRecorder with options failed, trying bare:', e);
            this.mediaRecorder = new MediaRecorder(this.stream);
        }

        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) this.chunks.push(e.data);
        };

        // Request data every 250ms so short recordings still capture audio
        this.mediaRecorder.start(250);
    }

    /** Stop recording and return the audio Blob. */
    stop() {
        return new Promise((resolve, reject) => {
            if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
                console.warn('MediaRecorder not active, returning empty blob');
                resolve(new Blob([], { type: 'audio/webm' }));
                return;
            }

            this.mediaRecorder.onstop = () => {
                const mimeType = this.mediaRecorder.mimeType || 'audio/webm';
                const blob = new Blob(this.chunks, { type: mimeType });
                console.log('Recorded blob:', blob.size, 'bytes,', mimeType);

                if (blob.size < 200) {
                    console.warn('Recording too short — may not transcribe');
                }

                resolve(blob);
            };

            this.mediaRecorder.onerror = (e) => {
                console.error('MediaRecorder error:', e);
                reject(e);
            };

            this.mediaRecorder.stop();
        });
    }

    /**
     * Play base64-encoded WAV through speakers.
     * Connects to AnalyserNode so callers can read amplitude for animation.
     * Returns a Promise that resolves when playback ends.
     */
    async play(base64Wav) {
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }

        const binary = atob(base64Wav);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

        const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);

        this.isPlaying = true;

        return new Promise((resolve) => {
            source.onended = () => {
                this.isPlaying = false;
                resolve();
            };
            source.start();
        });
    }

    /**
     * Read current audio amplitude (0–1).
     * Call this in a requestAnimationFrame loop during playback.
     */
    getAmplitude() {
        if (!this.analyser || !this.isPlaying) return 0;
        const data = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(data);
        const voiceBins = data.slice(0, 40);
        const sum = voiceBins.reduce((a, b) => a + b, 0);
        return Math.min(sum / (voiceBins.length * 180), 1);
    }
}