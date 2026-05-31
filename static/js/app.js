/**
 * MirrorApp — wires audio, face, API, and conversation history together.
 */
(async function () {
    const audio = new AudioManager();
    const face = new FaceController();

    const micBtn       = document.getElementById('mic-btn');
    const clearBtn     = document.getElementById('clear-btn');
    const exportBtn    = document.getElementById('export-btn');    
    const importBtn         = document.getElementById('import-session-btn');
    const importFileInput   = document.getElementById('import-file-input');
    const statusEl     = document.getElementById('status');
    const userTextEl   = document.getElementById('user-text');
    const mirrorTextEl = document.getElementById('mirror-text');
    const historyBtn   = document.getElementById('history-btn');
    const sidebar      = document.getElementById('sidebar');
    const overlay      = document.getElementById('sidebar-overlay');
    const sessionList  = document.getElementById('session-list');
    const newSessionBtn = document.getElementById('new-session-btn');
    const sessionTitle = document.getElementById('session-title');
    const convLog      = document.getElementById('conversation-log');
    const faceToggle    = document.getElementById('face-toggle');
    const defaultFace   = document.getElementById('default-face').value || 'face';

    let recording = false;
    let processing = false;

    // ── Init mic ────────────────────────────────────
    try {
        await audio.init();
    } catch (err) {
        statusEl.textContent = 'mic access denied';
        console.error('Mic init failed:', err);
        return;
    }
    
    // Pre-load the transform sound
    const transformSound = new Audio('/static/audio/transform.wav');
    transformSound.volume = 0.5;  // adjust to taste (0.0 – 1.0)

    const transformVolume = parseFloat(document.getElementById('transform-volume').value) || 0.5;
    transformSound.volume = transformVolume;
    
    // Resting face - not bitch face...
    face.setState('idle');

    // ── Theme & Face Toggle ────────────────────────
    const themeToggle = document.getElementById('theme-toggle');
    const defaultTheme = document.getElementById('default-theme').value || 'mirror';

    function getTheme() {
        return localStorage.getItem('mirror-theme') || defaultTheme;
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('mirror-theme', theme);
    }
    
    function getFace() {
        return localStorage.getItem('mirror-face') || defaultFace;
    }

    // Ensure theme is applied (backup for the inline script)
    setTheme(getTheme());

    // Load our session
    loadCurrentSession();


    // ── Push-to-talk ────────────────────────────────
    micBtn.addEventListener('click', toggleRecording);

    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && !e.repeat && !processing && !sidebarOpen()) {
            e.preventDefault();
            toggleRecording();
        }
    });

    clearBtn.addEventListener('click', async () => {
        await fetch('/api/clear', { method: 'POST' });
        clearTranscript();
        statusEl.textContent = 'conversation cleared';
        sessionTitle.textContent = 'new conversation';
        setTimeout(() => { statusEl.textContent = 'tap mic or press space'; }, 2000);
    });
    
    exportBtn.addEventListener('click', () => {
        const sid = sessionTitle.dataset.sessionId;
        if (sid) {
            exportSession(sid);
        } else {
            statusEl.textContent = 'no conversation to export';
            setTimeout(() => { statusEl.textContent = 'tap mic or press space'; }, 2000);
        }
    });

    importBtn.addEventListener('click', () => {
        importFileInput.click();
    });

    importFileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Reset input so the same file can be re-imported if needed
        importFileInput.value = '';

        const form = new FormData();
        form.append('file', file);

        try {
            const resp = await fetch('/api/sessions/import', {
                method: 'POST',
                body: form,
            });

            const data = await resp.json();

            if (!resp.ok) {
                showToast(`Import failed: ${data.error}`);
                return;
            }

            // Switch to the imported session
            const sResp = await fetch(`/api/sessions/${data.session_id}/switch`, { method: 'POST' });
            const sData = await sResp.json();
            displaySessionMessages(sData.session, sData.messages);
            await loadSessions(data.session_id);

            showToast(`Imported "${data.title}" — ${data.message_count} messages`);
            toggleSidebar(false);

        } catch (err) {
            console.error('Import error:', err);
            showToast('Import failed — check the file format');
        }
    });

    themeToggle.addEventListener('click', () => {
        const current = getTheme();
        const next = current === 'mirror' ? 'slate' : 'mirror';
        setTheme(next);
    });

    faceToggle.addEventListener('click', () => {
        const current = getFace();
        const next = current === 'face' ? 'hal' : 'face';

        // Play transform sound
        transformSound.currentTime = 0;  // rewind if clicked rapidly
        transformSound.play().catch(() => {});  // ignore autoplay errors

        face.setMode(next);
    });


    // ── Sidebar ─────────────────────────────────────
    historyBtn.addEventListener('click', () => toggleSidebar(true));
    overlay.addEventListener('click', () => toggleSidebar(false));

    newSessionBtn.addEventListener('click', async () => {
        const resp = await fetch('/api/sessions', { method: 'POST' });
        const data = await resp.json();
        clearTranscript();
        sessionTitle.textContent = 'new conversation';
        await loadSessions(data.session_id);
        toggleSidebar(false);
    });

    function sidebarOpen() {
        return sidebar.classList.contains('open');
    }

    function toggleSidebar(open) {
        sidebar.classList.toggle('open', open);
        overlay.classList.toggle('visible', open);
        if (open) loadSessions();
    }

    async function loadSessions(currentId) {
        const resp = await fetch('/api/sessions');
        const data = await resp.json();
        const current = currentId || data.current;

        sessionList.innerHTML = '';
        data.sessions.forEach(s => {
            const li = document.createElement('li');
            li.className = 'session-item' + (s.id === current ? ' active' : '');

            const ago = timeAgo(s.updated_at);

            li.innerHTML = `
                <div class="session-item-info">
                    <div class="session-item-title">${escapeHtml(s.title)}</div>
                    <div class="session-item-meta">${s.message_count} messages · ${ago}</div>
                </div>
                <button class="session-export" title="Export">↓</button>
                <button class="session-delete" title="Delete">✕</button>
            `;

            li.querySelector('.session-item-info').addEventListener('click', async () => {
                const resp = await fetch(`/api/sessions/${s.id}/switch`, { method: 'POST' });
                const result = await resp.json();
                displaySessionMessages(result.session, result.messages);
                toggleSidebar(false);
            });

            li.querySelector('.session-delete').addEventListener('click', async (e) => {
                e.stopPropagation();
                await fetch(`/api/sessions/${s.id}`, { method: 'DELETE' });
                await loadSessions();
            });
            
            li.querySelector('.session-export').addEventListener('click', (e) => {
                e.stopPropagation();
                exportSession(s.id);
            });

            sessionList.appendChild(li);
        });
    }

    async function loadCurrentSession() {
        try {
            const resp = await fetch('/api/sessions');
            const data = await resp.json();
            if (data.current) {
                sessionTitle.dataset.sessionId = data.current;
                const sResp = await fetch(`/api/sessions/${data.current}`);
                const sData = await sResp.json();
                displaySessionMessages(sData.session, sData.messages);
            }
        } catch (e) {
            console.log('No existing session');
        }
    }

    function displaySessionMessages(session, messages) {
        sessionTitle.textContent = session.title || 'new conversation';
        sessionTitle.dataset.sessionId = session.id;
        convLog.innerHTML = '';
        userTextEl.textContent = '';
        mirrorTextEl.textContent = '';

        messages.forEach(m => {
            const div = document.createElement('div');
            div.className = `log-message ${m.role}`;
            div.textContent = m.role === 'user' ? `"${m.content}"` : m.content;
            convLog.appendChild(div);
        });

        convLog.scrollTop = convLog.scrollHeight;
    }


    // ── Recording ───────────────────────────────────
    async function toggleRecording() {
        if (processing) return;

        if (!recording) {
            recording = true;
            micBtn.classList.add('recording');
            face.setState('listening');
            statusEl.textContent = 'listening…';
            userTextEl.textContent = '';
            mirrorTextEl.textContent = '';
            audio.start();
        } else {
            recording = false;
            processing = true;
            micBtn.classList.remove('recording');
            face.setState('thinking');
            statusEl.textContent = 'thinking…';

            const blob = await audio.stop();
            await processAudio(blob);

            processing = false;
            face.setState('idle');
            statusEl.textContent = 'tap mic or press space';
        }
    }


    // ── Pipeline ────────────────────────────────────
    async function processAudio(blob) {
        if (blob.size < 200) {
            mirrorTextEl.textContent = 'recording was too short — try holding the mic longer';
            statusEl.textContent = 'tap mic or press space';
            return;
        }

        const form = new FormData();
        form.append('audio', blob, 'recording.webm');


        try {
            const resp = await fetch('/api/converse', {
                method: 'POST',
                body: form,
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.error || 'Server error');
            }

            const data = await resp.json();

            // Set our session ID for tracking and exporting
            if (data.session_id) {
                sessionTitle.dataset.sessionId = data.session_id;
            }

            // Show transcript
            if (data.user_text) {
                userTextEl.textContent = `"${data.user_text}"`;
                appendToLog('user', data.user_text);
            }
            mirrorTextEl.textContent = data.response_text;
            appendToLog('assistant', data.response_text);

            // Update session title
            if (data.user_text && sessionTitle.textContent === 'new conversation') {
                const title = data.user_text.substring(0, 80);
                sessionTitle.textContent = title;
            }

            // Play audio with mouth sync
            if (data.audio_b64) {
                face.setState('speaking');
                statusEl.textContent = 'speaking…';
                startMouthSync();
                await audio.play(data.audio_b64);
                stopMouthSync();
            }
        } catch (err) {
            console.error('Pipeline error:', err);
            mirrorTextEl.textContent = 'something went wrong — try again';
            statusEl.textContent = 'error';
        }
    }

    function appendToLog(role, content) {
        const div = document.createElement('div');
        div.className = `log-message ${role}`;
        div.textContent = role === 'user' ? `"${content}"` : content;
        convLog.appendChild(div);
        convLog.scrollTop = convLog.scrollHeight;
    }

    function clearTranscript() {
        userTextEl.textContent = '';
        mirrorTextEl.textContent = '';
        convLog.innerHTML = '';
    }


// ── Amplitude sync loop ─────────────────────
    let mouthAnimFrame = null;

    function startMouthSync() {
        function loop() {
            const amp = audio.getAmplitude();
            face.setAmplitude(amp);           // ← was face.setMouthAmplitude(amp)
            mouthAnimFrame = requestAnimationFrame(loop);
        }
        loop();
    }

    function stopMouthSync() {
        if (mouthAnimFrame) {
            cancelAnimationFrame(mouthAnimFrame);
            mouthAnimFrame = null;
        }
        face.setAmplitude(0);                 // ← was face.setMouthAmplitude(0)
    }


    // ── Helpers ─────────────────────────────────────
    function escapeHtml(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    function timeAgo(isoStr) {
        const diff = Date.now() - new Date(isoStr).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        const days = Math.floor(hrs / 24);
        return `${days}d ago`;
    }

    function showToast(message) {
        // Remove existing toast if any
        const existing = document.querySelector('.import-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'import-toast';
        toast.textContent = message;
        document.body.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('visible');
        });

        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }


    // ── Export ──────────────────────────────────
    function exportSession(sessionId) {
        // Trigger browser download via hidden link
        const a = document.createElement('a');
        a.href = `/api/sessions/${sessionId}/export`;
        a.download = '';  // server sets the filename
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

})();
