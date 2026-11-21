/**
 * YatraPilot AI — Main Frontend Application
 * Premium UI + Real Agora Voice Integration
 */

'use strict';

// ============================================================
// STATE
// ============================================================

const State = {
    conversationHistory: [],
    pendingApproval: null,
    isSending: false,
    voice: {
        state: 'IDLE', // 'IDLE' | 'WELCOME' | 'RECORDING' | 'PREVIEW' | 'PROCESSING' | 'SPEAKING' | 'ERROR'
        mediaStream: null,
        mediaRecorder: null,
        audioChunks: [],
        recognition: null,
        timerInterval: null,
        welcomeTimer: null,
        welcomeCountInterval: null,
        silenceTimer: null,
        silenceCountdownInterval: null,
        silenceCountdownRemaining: 5,
        durationSeconds: 0,
        transcript: '',
        interimTranscript: '',
        audioElement: null,
        isSpeakerMuted: false,
        sessionGreetingPlayed: false
    },
    transport: {
        currentOrigin: 'Delhi',
        currentDest: 'Jaipur',
        currentCategory: 'all',
        allOptions: [],
        filteredOptions: [],
        routeSummary: null,
        map: null,
        routeLayer: null,
        markersLayer: null,
        mapConfig: null,
        hasSearched: false
    }
};

// ============================================================
// VIEW SWITCHING
// ============================================================

function showLanding() {
    stopMurfAudio(true);
    document.getElementById('landingPage').style.display = '';
    document.getElementById('voicePage').style.display = 'none';
    document.getElementById('assistantPage').style.display = 'none';
    const tp = document.getElementById('transportPage');
    if (tp) tp.style.display = 'none';
    document.getElementById('navbar').style.display = '';
    document.getElementById('navbar').style.background = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showVoiceAssistant() {
    document.getElementById('landingPage').style.display = 'none';
    document.getElementById('assistantPage').style.display = 'none';
    const tp = document.getElementById('transportPage');
    if (tp) tp.style.display = 'none';
    document.getElementById('voicePage').style.display = 'flex';
    document.getElementById('navbar').style.display = 'none'; // immersive full-screen voice

    // Check if greeting has played in this voice session
    if (!State.voice.sessionGreetingPlayed) {
        // Step 1: Wait exactly 3 seconds after the voice dashboard becomes visible
        transitionVoiceState('WELCOME', 'Welcome to YatraPilot AI · Initializing in 3s...');

        let remainingSecs = 3;
        const countdownEl = document.getElementById('voiceWelcomeCountdown');
        const countdownText = document.getElementById('voiceCountdownText');
        const captionEl = document.getElementById('voiceWelcomeCaption');

        if (countdownEl) countdownEl.style.display = 'inline-flex';
        if (countdownText) countdownText.textContent = `Starting voice greeting in ${remainingSecs}s...`;
        if (captionEl) captionEl.textContent = `Welcome to YatraPilot AI! Starting voice greeting in ${remainingSecs}s...`;

        if (State.voice.welcomeCountInterval) clearInterval(State.voice.welcomeCountInterval);
        State.voice.welcomeCountInterval = setInterval(() => {
            remainingSecs--;
            if (remainingSecs > 0) {
                if (countdownText) countdownText.textContent = `Starting voice greeting in ${remainingSecs}s...`;
                if (captionEl) captionEl.textContent = `Welcome to YatraPilot AI! Starting voice greeting in ${remainingSecs}s...`;
            }
        }, 1000);

        if (State.voice.welcomeTimer) clearTimeout(State.voice.welcomeTimer);
        State.voice.welcomeTimer = setTimeout(() => {
            clearInterval(State.voice.welcomeCountInterval);
            State.voice.welcomeCountInterval = null;
            if (countdownEl) countdownEl.style.display = 'none';

            // Step 2 & 3 & 4: Automatically play welcome message using Murf AI voice
            playInitialSpokenGreeting();
        }, 3000);

    } else {
        // Return to existing active session without replaying greeting
        transitionVoiceState('IDLE', 'Ready · Tap microphone to speak');
    }
}

function showTextChat() {
    stopMurfAudio(true);
    document.getElementById('landingPage').style.display = 'none';
    document.getElementById('voicePage').style.display = 'none';
    const tp = document.getElementById('transportPage');
    if (tp) tp.style.display = 'none';
    document.getElementById('assistantPage').style.display = '';
    document.getElementById('navbar').style.display = '';
    document.getElementById('navbar').style.background = 'rgba(255,255,255,0.97)';
    renderWelcome();
    setTimeout(() => document.getElementById('chatInput')?.focus(), 100);
}

function showTransportMarketplace() {
    stopMurfAudio(true);
    document.getElementById('landingPage').style.display = 'none';
    document.getElementById('voicePage').style.display = 'none';
    document.getElementById('assistantPage').style.display = 'none';
    const tp = document.getElementById('transportPage');
    if (tp) tp.style.display = 'block';
    document.getElementById('navbar').style.display = '';
    document.getElementById('navbar').style.background = 'rgba(255,255,255,0.98)';
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Initialize search on first visit or invalidate map size
    if (!State.transport.hasSearched) {
        triggerTransportSearch();
    } else if (State.transport.map) {
        setTimeout(() => {
            State.transport.map.invalidateSize();
        }, 200);
    }
}

// Backward compatibility alias for showAssistant
function showAssistant() {
    showVoiceAssistant();
}

function endVoiceConversation() {
    // 1. Cancel welcome timers if pending
    if (State.voice.welcomeTimer) {
        clearTimeout(State.voice.welcomeTimer);
        State.voice.welcomeTimer = null;
    }
    if (State.voice.welcomeCountInterval) {
        clearInterval(State.voice.welcomeCountInterval);
        State.voice.welcomeCountInterval = null;
    }
    const countdownEl = document.getElementById('voiceWelcomeCountdown');
    if (countdownEl) countdownEl.style.display = 'none';

    // Clear silence countdown timer
    clearSilenceTimer();

    // 2. Stop audio playback cleanly
    stopMurfAudio(true);

    // 3. Stop microphone & release all tracks immediately
    releaseMicrophone();

    // 4. Reset voice session state so next new session plays the greeting
    State.voice.sessionGreetingPlayed = false;
    State.voice.transcript = '';
    State.voice.interimTranscript = '';
    transitionVoiceState('IDLE');

    // 5. Clear dialogue stream for clean new session
    const stream = document.getElementById('voiceDialogueStream');
    if (stream) stream.innerHTML = '';

    // 6. Return to landing page
    showLanding();
}

function startChat(prompt) {
    showTextChat();
    setTimeout(() => {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = prompt;
            autoResize(input);
            sendMessage();
        }
    }, 150);
}

function sendQuickPrompt(text) {
    const input = document.getElementById('chatInput');
    if (input) {
        input.value = text;
        autoResize(input);
        sendMessage();
    }
}

// ============================================================
// WELCOME SCREEN
// ============================================================

function renderWelcome() {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    // Only render if container is empty
    if (container.children.length > 0) return;

    container.innerHTML = `
        <div class="chat-welcome">
            <div class="welcome-avatar">✈</div>
            <div class="welcome-title">Hello! I'm YatraPilot AI</div>
            <div class="welcome-sub">Ask me anything about travel planning — destinations, weather, attractions, budgets or complete itineraries.</div>
            <div class="welcome-chips">
                <button class="welcome-chip" onclick="sendQuickPrompt('Plan a 5-day trip to Goa for 2 people')">🏖 Plan a Goa trip</button>
                <button class="welcome-chip" onclick="sendQuickPrompt('What is the weather in Rajasthan today?')">🌤 Rajasthan weather</button>
                <button class="welcome-chip" onclick="sendQuickPrompt('Find tourist attractions in Mumbai')">🗺 Mumbai attractions</button>
                <button class="welcome-chip" onclick="sendQuickPrompt('Estimate budget for 7 days in Kerala for 2 people, mid-range')">💰 Budget estimate</button>
            </div>
        </div>
    `;
}

function clearWelcome() {
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.remove();
}

// ============================================================
// CHAT — SEND & RECEIVE
// ============================================================

async function sendMessage() {
    if (State.isSending) return;

    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const message = input?.value.trim();

    if (!message) return;

    // Clear welcome screen
    clearWelcome();

    // Render user bubble
    appendMessage('user', message);

    // Clear input and disable
    input.value = '';
    autoResize(input);
    State.isSending = true;
    if (sendBtn) sendBtn.disabled = true;

    // Update conversation history
    State.conversationHistory.push({ role: 'user', content: message });

    // Show typing indicator
    const loadingRow = appendLoading();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                history: State.conversationHistory.slice(0, -1) // exclude current msg
            })
        });

        loadingRow.remove();

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error || `Server error ${response.status}`);
        }

        const data = await response.json();
        const reply = data.response || '';

        // Update history
        State.conversationHistory.push({ role: 'assistant', content: reply });

        // Check for approval requests
        if (data.approval_required) {
            State.pendingApproval = data.approval_data;
            appendMessage('assistant', reply);
            showApprovalBanner(data.approval_data);
        } else {
            appendMessage('assistant', reply);
        }

    } catch (err) {
        loadingRow.remove();
        appendMessage('assistant', `Sorry, I encountered an error: **${err.message}**. Please try again.`, 'error');
        console.error('[YatraPilot] Chat error:', err);
    } finally {
        State.isSending = false;
        if (sendBtn) sendBtn.disabled = false;
        input.focus();
    }
}

// ============================================================
// MESSAGE RENDERING
// ============================================================

function appendMessage(role, text, type = '') {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const formatted = formatMarkdown(text);
    const errorClass = type === 'error' ? ' msg-error' : '';

    if (role === 'assistant') {
        row.innerHTML = `
            <div class="msg-avatar">✈</div>
            <div class="msg-bubble${errorClass}">${formatted}</div>
        `;
    } else {
        row.innerHTML = `<div class="msg-bubble">${formatted}</div>`;
    }

    container.appendChild(row);
    scrollToBottom();
    return row;
}

function appendLoading() {
    const container = document.getElementById('chatMessages');
    if (!container) return document.createElement('div');

    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.innerHTML = `
        <div class="msg-avatar">✈</div>
        <div class="msg-bubble loading">
            <div class="typing-dots">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    container.appendChild(row);
    scrollToBottom();
    return row;
}

function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    if (container) container.scrollTop = container.scrollHeight;
}

function clearChat() {
    State.conversationHistory = [];
    State.pendingApproval = null;
    const container = document.getElementById('chatMessages');
    if (container) {
        container.innerHTML = '';
        renderWelcome();
    }
}

// ============================================================
// MARKDOWN FORMATTER
// ============================================================

function formatMarkdown(text) {
    if (!text) return '';

    // Escape HTML first
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Inline code
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');

    // Convert markdown headings to bold
    html = html.replace(/^#{1,3}\s+(.+)$/gm, '<strong>$1</strong>');

    // Bullet lists
    html = html.replace(/^[\-\*]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

    // Numbered lists
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

    // Paragraphs — split on double newline
    html = html.split(/\n\n+/).map(block => {
        block = block.trim();
        if (!block) return '';
        if (block.startsWith('<ul>') || block.startsWith('<li>')) return block;
        return `<p>${block.replace(/\n/g, '<br>')}</p>`;
    }).join('');

    return html;
}

// ============================================================
// APPROVAL FLOW (HITL)
// ============================================================

function showApprovalBanner(approvalData) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    const banner = document.createElement('div');
    banner.className = 'approval-banner';
    banner.id = 'approvalBanner';
    banner.innerHTML = `
        <span class="approval-text">✅ Save this trip to your itineraries?</span>
        <div class="approval-actions">
            <button class="btn-approve" onclick="handleApproval(true)">Yes, Save</button>
            <button class="btn-reject" onclick="handleApproval(false)">No Thanks</button>
        </div>
    `;
    container.appendChild(banner);
    scrollToBottom();
}

async function handleApproval(approved) {
    // Hide modal if shown
    const modal = document.getElementById('approvalModal');
    if (modal) modal.style.display = 'none';

    // Remove banner
    const banner = document.getElementById('approvalBanner');
    if (banner) banner.remove();

    if (!State.pendingApproval) return;

    const data = State.pendingApproval;
    State.pendingApproval = null;

    if (!approved) {
        appendMessage('assistant', "No problem! I won't save the trip. Let me know if you'd like to make changes.");
        return;
    }

    // Approve via backend
    try {
        const response = await fetch('/api/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                channel: data.channel || 'web',
                action: 'save_trip',
                approved: true,
                trip_data: data
            })
        });

        if (!response.ok) throw new Error('Approval failed');

        const result = await response.json();
        appendMessage('assistant', `✅ **Trip saved successfully!** Your ${data.destination} trip has been stored in your itineraries${result.result ? ` (ID: ${result.result})` : ''}.`);

    } catch (err) {
        appendMessage('assistant', `Sorry, I couldn't save the trip. ${err.message}`, 'error');
    }
}

// ============================================================
// INPUT HANDLING
// ============================================================

function autoResize(textarea) {
    if (!textarea) return;
    textarea.style.height = 'auto';
    const maxH = 150;
    textarea.style.height = Math.min(textarea.scrollHeight, maxH) + 'px';
}

function initInputHandlers() {
    const input = document.getElementById('chatInput');
    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        input.addEventListener('input', () => autoResize(input));
    }

    const tOrigin = document.getElementById('transportOrigin');
    const tDest = document.getElementById('transportDest');
    [tOrigin, tDest].forEach(el => {
        if (el) {
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    triggerTransportSearch();
                }
            });
        }
    });

    const dateInput = document.getElementById('transportDate');
    if (dateInput && !dateInput.value) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }
}

// ============================================================
// HEALTH CHECK & STATUS
// ============================================================

async function checkHealth() {
    const dot = document.getElementById('aiOnlineDot');
    const statusText = document.getElementById('aiStatusText');

    try {
        const response = await fetch('/health', { signal: AbortSignal.timeout(5000) });
        if (response.ok) {
            if (dot) dot.classList.add('online');
            if (statusText) statusText.textContent = 'Online';
        } else {
            if (statusText) statusText.textContent = 'Degraded';
        }
    } catch {
        if (statusText) statusText.textContent = 'Offline';
    }
}

// ============================================================
// CENTERED VOICE-FIRST EXPERIENCE (MURF FALCON 2.1 + GEMINI)
// ============================================================

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || null;

const GREETING_TEXT = "Hi! I'm your YatraPilot AI travel agent. I'm here to help you plan your journeys, discover destinations, compare transportation options, check weather, and create your travel itinerary. Where would you like to go today?";

let audioContext = null;
let micAnalyserNode = null;
let playbackAnalyserNode = null;
let micSourceNode = null;
let playbackSourceNode = null;
let currentAudioEl = null;
let visualizerFrameId = null;

/**
 * Initializes AudioContext safely on user interaction
 */
function getAudioContext() {
    if (!audioContext) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
            audioContext = new AudioCtx();
        }
    }
    if (audioContext && audioContext.state === 'suspended') {
        audioContext.resume().catch(() => {});
    }
    return audioContext;
}

/**
 * Adds a chat message card into the Voice Dialogue Stream
 */
function addVoiceMessage(role, text) {
    const stream = document.getElementById('voiceDialogueStream');
    if (!stream) return;

    const msg = document.createElement('div');
    msg.className = `voice-dialogue-msg ${role}`;
    msg.innerHTML = `
        <div class="vd-avatar">${role === 'assistant' ? '✈' : '👤'}</div>
        <div class="vd-content">${formatMarkdown(text)}</div>
    `;
    stream.appendChild(msg);
    stream.scrollTop = stream.scrollHeight;
}

/**
 * Update Voice UI according to state:
 * 'IDLE' | 'WELCOME' | 'RECORDING' | 'PREVIEW' | 'PROCESSING' | 'SPEAKING' | 'ERROR'
 */
function transitionVoiceState(state, customText = '') {
    State.voice.state = state;

    const vWel = document.getElementById('vStateWelcome');
    const vIdle = document.getElementById('vStateIdle');
    const vRec = document.getElementById('vStateRecording');
    const vPrev = document.getElementById('vStatePreview');
    const vProc = document.getElementById('vStateProcessing');
    const vSpeak = document.getElementById('vStateSpeaking');

    const statusBadge = document.getElementById('voiceStatusBadge');
    const statusDot = document.getElementById('voiceStatusDot');
    const statusText = document.getElementById('voiceStatusText');
    const centerOrb = document.getElementById('centralVoiceOrb');
    const orbIcon = document.getElementById('orbCenterIcon');
    const eqBars = document.getElementById('voiceEqualizerBars');
    const durationCounter = document.getElementById('voiceDurationCounter');
    const liveFeedback = document.getElementById('voiceLiveFeedback');

    // Reset visibility of controls
    if (vWel) vWel.style.display = 'none';
    if (vIdle) vIdle.style.display = 'none';
    if (vRec) vRec.style.display = 'none';
    if (vPrev) vPrev.style.display = 'none';
    if (vProc) vProc.style.display = 'none';
    if (vSpeak) vSpeak.style.display = 'none';

    // Reset orb classes
    if (centerOrb) {
        centerOrb.classList.remove('recording', 'speaking');
    }
    if (statusDot) {
        statusDot.className = 'status-indicator-dot';
    }
    if (eqBars) {
        eqBars.classList.remove('active', 'speaking');
    }

    switch (state) {
        case 'WELCOME':
            if (vWel) vWel.style.display = 'flex';
            if (statusDot) statusDot.classList.add('welcome');
            if (statusText) statusText.textContent = customText || 'Welcome! Initializing in 3s...';
            if (orbIcon) orbIcon.textContent = '✈';
            if (durationCounter) durationCounter.style.display = 'none';
            if (liveFeedback) liveFeedback.textContent = '';
            break;

        case 'IDLE':
            if (vIdle) vIdle.style.display = 'flex';
            if (statusText) statusText.textContent = customText || 'Ready · Tap microphone to speak';
            if (orbIcon) orbIcon.textContent = '🎙';
            if (durationCounter) durationCounter.style.display = 'none';
            if (liveFeedback) liveFeedback.textContent = '';
            break;

        case 'RECORDING':
            if (vRec) vRec.style.display = 'flex';
            if (statusDot) statusDot.classList.add('recording');
            if (statusText) statusText.textContent = customText || 'Listening... · Speak naturally';
            if (centerOrb) centerOrb.classList.add('recording');
            if (orbIcon) orbIcon.textContent = '🎙';
            if (eqBars) eqBars.classList.add('active');
            if (durationCounter) {
                durationCounter.style.display = 'block';
                durationCounter.textContent = '0:00';
            }
            if (liveFeedback) liveFeedback.textContent = 'Listening for your travel question...';
            break;

        case 'PREVIEW':
            if (vPrev) vPrev.style.display = 'flex';
            if (statusText) statusText.textContent = customText || 'Transcript ready · Review & send';
            if (orbIcon) orbIcon.textContent = '✏';
            if (durationCounter) durationCounter.style.display = 'none';
            if (liveFeedback) liveFeedback.textContent = '';
            break;

        case 'PROCESSING':
            if (vProc) vProc.style.display = 'flex';
            if (statusDot) statusDot.classList.add('processing');
            if (statusText) statusText.textContent = customText || 'Consulting travel intelligence...';
            if (orbIcon) orbIcon.textContent = '✦';
            if (durationCounter) durationCounter.style.display = 'none';
            if (liveFeedback) liveFeedback.textContent = 'Generating real Murf voice audio...';
            break;

        case 'SPEAKING':
            if (vSpeak) vSpeak.style.display = 'flex';
            if (statusDot) statusDot.classList.add('speaking');
            if (statusText) statusText.textContent = customText || 'YatraPilot is speaking...';
            if (centerOrb) centerOrb.classList.add('speaking');
            if (orbIcon) orbIcon.textContent = '🔊';
            if (eqBars) eqBars.classList.add('speaking');
            if (durationCounter) durationCounter.style.display = 'none';
            break;

        case 'ERROR':
            if (vIdle) vIdle.style.display = 'flex';
            if (statusText) statusText.textContent = customText || 'Voice error occurred';
            if (orbIcon) orbIcon.textContent = '⚠';
            if (durationCounter) durationCounter.style.display = 'none';
            if (liveFeedback) liveFeedback.textContent = customText;
            break;
    }
}

/**
 * Plays Murf Falcon 2.1 generated MP3 audio with real-time Web Audio API visualizer.
 * Automatically halts any active microphone capture before starting audio.
 */
function playMurfAudio(audioSrcOrB64, onComplete = null) {
    // 1. Release microphone to prevent audio playing into mic
    if (State.voice.state === 'RECORDING') {
        releaseMicrophone();
    }
    stopMurfAudio(false);

    const audio = new Audio();
    currentAudioEl = audio;

    if (audioSrcOrB64.startsWith('data:') || audioSrcOrB64.startsWith('http') || audioSrcOrB64.startsWith('/')) {
        audio.src = audioSrcOrB64;
    } else {
        audio.src = 'data:audio/mp3;base64,' + audioSrcOrB64;
    }

    if (State.voice.isSpeakerMuted) {
        audio.muted = true;
    }

    transitionVoiceState('SPEAKING', 'YatraPilot is speaking...');

    audio.onplay = () => {
        setupPlaybackVisualizer(audio);
    };

    audio.onended = () => {
        stopAudioVisualizer();
        currentAudioEl = null;
        if (onComplete) {
            onComplete();
        } else {
            transitionVoiceState('IDLE', 'Ready · Ask another travel question');
        }
    };

    audio.onerror = (e) => {
        console.warn('[Murf Audio] Playback error:', e);
        stopAudioVisualizer();
        currentAudioEl = null;
        transitionVoiceState('IDLE');
    };

    audio.play().catch(err => {
        console.warn('[Murf Audio] Play call deferred by browser:', err);
        transitionVoiceState('IDLE', 'Audio ready · Tap to speak with YatraPilot');
    });
}

/**
 * Stops Murf audio playback cleanly
 */
function stopMurfAudio(resetToIdle = true) {
    if (currentAudioEl) {
        try {
            currentAudioEl.pause();
            currentAudioEl.currentTime = 0;
            currentAudioEl.src = '';
        } catch (e) {}
        currentAudioEl = null;
    }
    stopAudioVisualizer();
    if (resetToIdle && State.voice.state === 'SPEAKING') {
        transitionVoiceState('IDLE');
    }
}

/**
 * Sets up isolated microphone visualizer.
 * CRITICAL AUDIO FIX: Connects ONLY to micAnalyserNode.
 * NEVER connects to ctx.destination — this eliminates the audio feedback / echo loop completely!
 */
function setupMicVisualizer(stream) {
    try {
        const ctx = getAudioContext();
        if (!ctx) return;

        if (micSourceNode) {
            try { micSourceNode.disconnect(); } catch (e) {}
            micSourceNode = null;
        }

        if (!micAnalyserNode) {
            micAnalyserNode = ctx.createAnalyser();
            micAnalyserNode.fftSize = 64;
            micAnalyserNode.smoothingTimeConstant = 0.8;
        }

        micSourceNode = ctx.createMediaStreamSource(stream);
        // Connect to analyser only. DO NOT connect micAnalyserNode to destination!
        micSourceNode.connect(micAnalyserNode);

        startVisualizerLoop(micAnalyserNode);
    } catch (e) {
        console.warn('[Mic Visualizer] Setup warning:', e);
    }
}

/**
 * Connects audio playback element to Web Audio API for visualizer output
 */
function setupPlaybackVisualizer(mediaElement) {
    try {
        const ctx = getAudioContext();
        if (!ctx) return;

        if (!playbackAnalyserNode) {
            playbackAnalyserNode = ctx.createAnalyser();
            playbackAnalyserNode.fftSize = 64;
            playbackAnalyserNode.smoothingTimeConstant = 0.8;
        }

        try {
            if (!playbackSourceNode || playbackSourceNode.mediaElement !== mediaElement) {
                playbackSourceNode = ctx.createMediaElementSource(mediaElement);
                playbackSourceNode.connect(playbackAnalyserNode);
                playbackAnalyserNode.connect(ctx.destination);
            }
        } catch (e) {
            // Already connected or cross-origin
        }

        startVisualizerLoop(playbackAnalyserNode);
    } catch (e) {
        console.warn('[Playback Visualizer] Setup warning:', e);
    }
}

/**
 * Visualizer animation loop driving equalizer bars & central orb
 */
function startVisualizerLoop(analyser) {
    stopAudioVisualizer();

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    const bars = document.querySelectorAll('#voiceEqualizerBars span');
    const orb = document.getElementById('centralVoiceOrb');

    function render() {
        visualizerFrameId = requestAnimationFrame(render);
        analyser.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
        }
        const avg = sum / dataArray.length;

        // Scale orb slightly with voice amplitude
        if (orb) {
            const scale = 1 + (avg / 255) * 0.14;
            orb.style.transform = `scale(${scale.toFixed(3)})`;
        }

        // Set bar heights
        if (bars && bars.length > 0) {
            const step = Math.floor(dataArray.length / bars.length) || 1;
            bars.forEach((bar, idx) => {
                const val = dataArray[idx * step] || avg;
                const h = Math.max(6, Math.min(36, (val / 255) * 36));
                bar.style.height = `${h.toFixed(1)}px`;
            });
        }
    }

    render();
}

/**
 * Stops visualizer animation
 */
function stopAudioVisualizer() {
    if (visualizerFrameId) {
        cancelAnimationFrame(visualizerFrameId);
        visualizerFrameId = null;
    }
    const orb = document.getElementById('centralVoiceOrb');
    if (orb) orb.style.transform = '';
    const bars = document.querySelectorAll('#voiceEqualizerBars span');
    bars.forEach(b => b.style.height = '8px');
}

/**
 * Releases microphone resources and stops speech recognition cleanly
 */
function releaseMicrophone() {
    clearSilenceTimer();

    if (State.voice.timerInterval) {
        clearInterval(State.voice.timerInterval);
        State.voice.timerInterval = null;
    }
    stopAudioVisualizer();

    if (micSourceNode) {
        try { micSourceNode.disconnect(); } catch (e) {}
        micSourceNode = null;
    }

    if (State.voice.recognition) {
        try {
            State.voice.recognition.onend = null;
            State.voice.recognition.onerror = null;
            State.voice.recognition.stop();
        } catch (e) {}
        State.voice.recognition = null;
    }

    if (State.voice.mediaStream) {
        try {
            State.voice.mediaStream.getTracks().forEach(track => {
                track.stop();
                track.enabled = false;
            });
        } catch (e) {}
        State.voice.mediaStream = null;
    }
}

/**
 * Clears the 5-second silence auto-submission timer and countdown UI
 */
function clearSilenceTimer() {
    if (State.voice.silenceTimer) {
        clearTimeout(State.voice.silenceTimer);
        State.voice.silenceTimer = null;
    }
    if (State.voice.silenceCountdownInterval) {
        clearInterval(State.voice.silenceCountdownInterval);
        State.voice.silenceCountdownInterval = null;
    }
    const countdownEl = document.getElementById('voiceSilenceCountdown');
    if (countdownEl) countdownEl.style.display = 'none';
}

/**
 * Gemini-style automatic voice submission:
 * Starts a 5-second silence countdown once speech is captured.
 * If 5 seconds elapse with silence and non-empty transcript, automatically
 * stops recording and sends the transcript to Gemini & Murf TTS.
 */
function resetAndStartSilenceTimer() {
    clearSilenceTimer();

    // Only run silence countdown if user is actively recording
    if (State.voice.state !== 'RECORDING') return;

    const textSoFar = (State.voice.transcript || State.voice.interimTranscript || '').trim();
    if (!textSoFar) return; // Do not auto-submit silence if no words were spoken

    State.voice.silenceCountdownRemaining = 5;
    const countdownEl = document.getElementById('voiceSilenceCountdown');
    const textEl = document.getElementById('silenceCountdownText');
    if (countdownEl) countdownEl.style.display = 'inline-flex';
    if (textEl) textEl.textContent = 'Silence detected · Sending in 5s...';

    State.voice.silenceCountdownInterval = setInterval(() => {
        State.voice.silenceCountdownRemaining--;
        if (State.voice.silenceCountdownRemaining > 0) {
            if (textEl) textEl.textContent = `Silence detected · Sending in ${State.voice.silenceCountdownRemaining}s...`;
        }
    }, 1000);

    State.voice.silenceTimer = setTimeout(() => {
        clearSilenceTimer();
        if (State.voice.state === 'RECORDING') {
            const finalSpeech = (State.voice.transcript || State.voice.interimTranscript || '').trim();
            if (finalSpeech) {
                console.log('[Voice] 5s silence auto-submitting speech:', finalSpeech);
                stopVoiceRecording();
                setTimeout(() => {
                    sendVoiceTranscript();
                }, 200);
            }
        }
    }, 5000);
}

/**
 * Automatically plays Murf's spoken greeting once per new voice session.
 * Displays greeting message in dialogue stream, animates visualizer,
 * and automatically starts microphone when the greeting finishes.
 */
function playInitialSpokenGreeting() {
    State.voice.sessionGreetingPlayed = true;

    // Show greeting message card in voice dialogue stream
    addVoiceMessage('assistant', GREETING_TEXT);

    // Update greeting caption
    const captionEl = document.getElementById('voiceGreetingCaption');
    if (captionEl) {
        captionEl.textContent = GREETING_TEXT;
    }

    // Play greeting audio; do NOT start microphone until greeting finishes
    playMurfAudio('/api/voice/greeting', () => {
        // Once greeting completes: activate microphone and indicate assistant is ready to listen
        console.log('[Voice] Greeting completed. Automatically activating microphone...');
        transitionVoiceState('RECORDING', 'Listening... · Speak naturally');
        setTimeout(() => {
            startVoiceRecording();
        }, 300);
    });
}

/**
 * Toggle speaker mute / unmute
 */
function toggleSpeakerMute() {
    State.voice.isSpeakerMuted = !State.voice.isSpeakerMuted;
    if (currentAudioEl) {
        currentAudioEl.muted = State.voice.isSpeakerMuted;
    }

    const iconOn = document.getElementById('iconSpeakerOn');
    const iconMuted = document.getElementById('iconSpeakerMuted');
    const label = document.getElementById('speakerLabel');

    if (State.voice.isSpeakerMuted) {
        if (iconOn) iconOn.style.display = 'none';
        if (iconMuted) iconMuted.style.display = '';
        if (label) label.textContent = 'Muted';
    } else {
        if (iconOn) iconOn.style.display = '';
        if (iconMuted) iconMuted.style.display = 'none';
        if (label) label.textContent = 'Audio On';
    }
}

/**
 * Start Voice Recording (User speaks naturally)
 * Implements hardware/browser echoCancellation, noiseSuppression, and autoGainControl.
 */
async function startVoiceRecording() {
    // 1. If welcome countdown is pending, cancel it immediately so user can record
    if (State.voice.welcomeTimer) {
        clearTimeout(State.voice.welcomeTimer);
        State.voice.welcomeTimer = null;
    }
    if (State.voice.welcomeCountInterval) {
        clearInterval(State.voice.welcomeCountInterval);
        State.voice.welcomeCountInterval = null;
    }
    const countdownEl = document.getElementById('voiceWelcomeCountdown');
    if (countdownEl) countdownEl.style.display = 'none';

    // 2. Stop any currently playing audio immediately (mutual exclusion prevents audio playing into mic)
    stopMurfAudio(false);

    State.voice.transcript = '';
    State.voice.interimTranscript = '';
    State.voice.durationSeconds = 0;

    // 3. Request microphone access with full echo cancellation constraints
    try {
        const audioConstraints = {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
            sampleRate: 48000
        };

        const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
        State.voice.mediaStream = stream;

        // Connect mic stream to isolated visualizer (NO loopback to speakers)
        setupMicVisualizer(stream);

    } catch (err) {
        console.error('[Voice] Mic permission error:', err);
        let errorMsg = 'Microphone permission denied. Please allow microphone access in your browser.';
        if (err.name === 'NotFoundError') {
            errorMsg = 'No microphone device was found.';
        }
        transitionVoiceState('ERROR', errorMsg);
        return;
    }

    // 4. Setup Browser Speech Recognition
    if (SpeechRecognition) {
        try {
            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            recognition.maxAlternatives = 1;

            recognition.onspeechstart = () => {
                clearSilenceTimer();
            };

            recognition.onresult = (event) => {
                let interim = '';
                let final = '';
                for (let i = 0; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        final += event.results[i][0].transcript + ' ';
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }
                State.voice.transcript = final.trim();
                State.voice.interimTranscript = interim.trim();

                const displayText = (State.voice.transcript ? State.voice.transcript + ' ' : '') + State.voice.interimTranscript;
                const feedbackEl = document.getElementById('voiceLiveFeedback');
                if (feedbackEl && displayText) {
                    feedbackEl.textContent = `Hearing: "${displayText.length > 55 ? '...' + displayText.slice(-52) : displayText}"`;
                }

                // 5-second silence auto-submission (Gemini-style)
                if (displayText.trim().length > 0) {
                    resetAndStartSilenceTimer();
                }
            };

            recognition.onspeechend = () => {
                const currentText = (State.voice.transcript || State.voice.interimTranscript || '').trim();
                if (currentText.length > 0) {
                    resetAndStartSilenceTimer();
                }
            };

            recognition.onerror = (event) => {
                console.warn('[STT] Recognition event error:', event.error);
                if (event.error === 'not-allowed') {
                    transitionVoiceState('ERROR', 'Microphone permission denied.');
                }
            };

            recognition.onend = () => {
                if (State.voice.state === 'RECORDING') {
                    try { recognition.start(); } catch (e) {}
                }
            };

            recognition.start();
            State.voice.recognition = recognition;
        } catch (e) {
            console.warn('[STT] Failed to initialize SpeechRecognition:', e);
        }
    }

    // 5. Update UI to RECORDING state & start timer
    transitionVoiceState('RECORDING');

    if (State.voice.timerInterval) clearInterval(State.voice.timerInterval);
    State.voice.timerInterval = setInterval(() => {
        State.voice.durationSeconds++;
        const mins = Math.floor(State.voice.durationSeconds / 60);
        const secs = State.voice.durationSeconds % 60;
        const formatted = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
        const timerEl = document.getElementById('voiceDurationCounter');
        if (timerEl) timerEl.textContent = formatted;
    }, 1000);
}

/**
 * Stop Voice Recording immediately and transition to PREVIEW
 */
function stopVoiceRecording() {
    if (State.voice.state !== 'RECORDING') return;

    // Clear silence countdown timer
    clearSilenceTimer();

    // 1. Gather recognized transcript BEFORE releasing hardware
    let finalTranscript = State.voice.transcript.trim();
    if (!finalTranscript && State.voice.interimTranscript.trim()) {
        finalTranscript = State.voice.interimTranscript.trim();
    }
    State.voice.transcript = finalTranscript;

    // 2. Release microphone hardware and recognition immediately
    releaseMicrophone();

    // 3. Transition to PREVIEW state
    transitionVoiceState('PREVIEW');

    const input = document.getElementById('voiceTranscriptInput');
    if (input) {
        input.value = finalTranscript || '';
        if (!finalTranscript) {
            input.placeholder = 'No speech detected. Please type your query or tap Record Again.';
        }
        input.focus();
    }
}

/**
 * Send the recognized & editable transcript to Gemini + Murf TTS
 */
async function sendVoiceTranscript() {
    clearSilenceTimer();

    const input = document.getElementById('voiceTranscriptInput');
    const message = (input && input.value.trim()) ? input.value.trim() : ((State.voice.transcript || State.voice.interimTranscript || '').trim());

    if (!message) {
        transitionVoiceState('PREVIEW', 'Please type or record a message first.');
        return;
    }

    if (State.isSending) return; // Prevent duplicate submissions
    State.isSending = true;

    const sendBtn = document.getElementById('btnVoiceSendQuery');
    if (sendBtn) sendBtn.disabled = true;

    // 1. Display user query card in voice dialogue stream
    addVoiceMessage('user', message);

    // 2. Transition to PROCESSING state
    transitionVoiceState('PROCESSING', 'Consulting Gemini & travel intelligence...');

    // 3. Hide previous transcript box if any
    const spokenBox = document.getElementById('voiceSpokenTranscriptBox');
    if (spokenBox) spokenBox.style.display = 'none';

    try {
        const response = await fetch('/api/voice/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                history: State.conversationHistory.slice(-6) // recent turns
            })
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error || `Server error (${response.status})`);
        }

        const data = await response.json();
        const replyText = data.response || 'I have planned your travel request.';
        const audioB64 = data.audio_base64;

        // Update multi-turn history
        State.conversationHistory.push({ role: 'user', content: message });
        State.conversationHistory.push({ role: 'assistant', content: replyText });

        // Display assistant response card in voice dialogue stream alongside audio
        addVoiceMessage('assistant', replyText);

        // Update spoken transcript text (hidden under optional toggle)
        const transcriptTextEl = document.getElementById('voiceSpokenTranscriptText');
        if (transcriptTextEl) {
            transcriptTextEl.textContent = replyText;
        }

        // Update greeting caption with a brief summary
        const captionEl = document.getElementById('voiceGreetingCaption');
        if (captionEl) {
            captionEl.textContent = replyText.length > 120 ? replyText.substring(0, 117) + '...' : replyText;
        }

        // Play the real Murf audio!
        if (audioB64) {
            playMurfAudio(audioB64, () => {
                transitionVoiceState('IDLE', 'Ready · Ask another travel question');
            });
        } else {
            transitionVoiceState('IDLE', 'Response received · Ask another question');
        }

    } catch (err) {
        console.error('[Voice Chat] Error:', err);
        transitionVoiceState('ERROR', `Could not complete request: ${err.message}`);
    } finally {
        State.isSending = false;
        if (sendBtn) sendBtn.disabled = false;
    }
}

/**
 * Record Again action
 */
function recordAgain() {
    const input = document.getElementById('voiceTranscriptInput');
    if (input) input.value = '';
    State.voice.transcript = '';
    State.voice.interimTranscript = '';
    startVoiceRecording();
}

/**
 * Cancel Voice Recording and return to IDLE
 */
function cancelVoiceRecording() {
    clearSilenceTimer();
    releaseMicrophone();
    transitionVoiceState('IDLE');
}

/**
 * Quick preset chip submission in voice mode
 */
function submitVoicePreset(presetText) {
    const input = document.getElementById('voiceTranscriptInput');
    if (input) input.value = presetText;
    State.voice.transcript = presetText;
    sendVoiceTranscript();
}

/**
 * Toggle display of spoken response transcript
 */
function toggleSpokenTranscript() {
    const box = document.getElementById('voiceSpokenTranscriptBox');
    const btn = document.getElementById('btnToggleTranscript');
    if (!box) return;

    if (box.style.display === 'none' || !box.style.display) {
        box.style.display = 'block';
        if (btn) btn.textContent = 'Hide Transcript';
    } else {
        box.style.display = 'none';
        if (btn) btn.textContent = 'Show Transcript';
    }
}

// ============================================================
// HTML & JS ESCAPING HELPERS
// ============================================================

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function escapeJs(str) {
    if (!str) return '';
    return String(str).replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// ============================================================
// TRANSPORTATION & MOBILITY MARKETPLACE
// ============================================================

function swapTransportRoute() {
    const originInput = document.getElementById('transportOrigin');
    const destInput = document.getElementById('transportDest');
    if (!originInput || !destInput) return;

    const temp = originInput.value;
    originInput.value = destInput.value;
    destInput.value = temp;

    // Re-trigger search with swapped cities
    triggerTransportSearch();
}

async function triggerTransportSearch() {
    const origin = (document.getElementById('transportOrigin')?.value || 'Delhi').trim();
    const dest = (document.getElementById('transportDest')?.value || 'Jaipur').trim();
    const date = document.getElementById('transportDate')?.value || '';
    const passengers = parseInt(document.getElementById('transportPassengers')?.value || '12', 10);
    const category = State.transport.currentCategory || 'all';

    State.transport.currentOrigin = origin;
    State.transport.currentDest = dest;
    State.transport.hasSearched = true;

    const grid = document.getElementById('transportResultsGrid');
    if (grid) {
        grid.innerHTML = `
            <div class="transport-loading-state">
                <div class="transport-spinner"></div>
                <div class="transport-loading-title">Discovering routes, carriers and rental options...</div>
                <div class="transport-loading-sub">Querying MapTiler, India GTFS &amp; verified provider networks for ${escapeHtml(origin)} ➔ ${escapeHtml(dest)}</div>
            </div>
        `;
    }

    try {
        // 1. Search options from backend
        const searchResp = await fetch('/api/transport/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin,
                destination: dest,
                date,
                passengers,
                category
            })
        });

        const searchData = await searchResp.json();
        if (searchData && searchData.options && searchData.options.length > 0) {
            State.transport.allOptions = searchData.options;
            updateCategoryCounts(State.transport.allOptions);
            filterTransportCategory(State.transport.currentCategory, false);
        } else {
            if (grid) {
                grid.innerHTML = `<div class="transport-empty-state">Could not find routes for ${escapeHtml(origin)} ➔ ${escapeHtml(dest)}. Please verify city names.</div>`;
            }
        }

        // 2. Load interactive route & map
        await loadRouteOnMap(origin, dest);

    } catch (err) {
        console.error('[Transport] Search failed:', err);
        if (grid) {
            grid.innerHTML = `<div class="transport-error-state">Failed to load transport options. Please try again.</div>`;
        }
    }
}

function updateCategoryCounts(options) {
    const counts = {
        all: options.length,
        bus: 0,
        train: 0,
        flight: 0,
        taxi: 0,
        car_rental: 0,
        tempo_traveller: 0,
        private_coach: 0,
        registered_fleet: 0
    };

    options.forEach(opt => {
        const cat = opt.category;
        if (counts[cat] !== undefined) counts[cat]++;
        if (opt.details?.is_neon_registered || (opt.source && opt.source.includes('Neon DB'))) {
            counts.registered_fleet++;
        }
    });

    const elCountAll = document.getElementById('countAll');
    const elCountBus = document.getElementById('countBus');
    const elCountTrain = document.getElementById('countTrain');
    const elCountFlight = document.getElementById('countFlight');
    const elCountTaxi = document.getElementById('countTaxi');
    const elCountCarRental = document.getElementById('countCarRental');
    const elCountTempo = document.getElementById('countTempo');
    const elCountCoach = document.getElementById('countCoach');
    const elCountRegistered = document.getElementById('countRegistered');

    if (elCountAll) elCountAll.textContent = counts.all;
    if (elCountBus) elCountBus.textContent = counts.bus;
    if (elCountTrain) elCountTrain.textContent = counts.train;
    if (elCountFlight) elCountFlight.textContent = counts.flight;
    if (elCountTaxi) elCountTaxi.textContent = counts.taxi;
    if (elCountCarRental) elCountCarRental.textContent = counts.car_rental;
    if (elCountTempo) elCountTempo.textContent = counts.tempo_traveller;
    if (elCountCoach) elCountCoach.textContent = counts.private_coach;
    if (elCountRegistered) elCountRegistered.textContent = counts.registered_fleet;
}

function filterTransportCategory(category, updatePills = true) {
    State.transport.currentCategory = category;

    if (updatePills) {
        document.querySelectorAll('.transport-category-pills .tpill').forEach(pill => {
            if (pill.getAttribute('data-category') === category) {
                pill.classList.add('active');
            } else {
                pill.classList.remove('active');
            }
        });
    }

    if (category === 'all') {
        State.transport.filteredOptions = [...State.transport.allOptions];
    } else if (category === 'registered_fleet') {
        State.transport.filteredOptions = State.transport.allOptions.filter(o =>
            o.details?.is_neon_registered || (o.source && o.source.includes('Neon DB'))
        );
    } else {
        State.transport.filteredOptions = State.transport.allOptions.filter(o => o.category === category);
    }

    sortTransportResults();
}

function sortTransportResults() {
    const sortVal = document.getElementById('transportSort')?.value || 'recommended';
    let sorted = [...State.transport.filteredOptions];

    if (sortVal === 'price_asc') {
        sorted.sort((a, b) => (a.price_estimate_inr || 999999) - (b.price_estimate_inr || 999999));
    } else if (sortVal === 'capacity_desc') {
        sorted.sort((a, b) => (b.capacity || 1) - (a.capacity || 1));
    }

    renderTransportCards(sorted);
}

function renderTransportCards(options) {
    const grid = document.getElementById('transportResultsGrid');
    if (!grid) return;

    if (!options || options.length === 0) {
        grid.innerHTML = `
            <div class="transport-empty-state">
                <div class="empty-icon">🔍</div>
                <h3>No options found for this category</h3>
                <p>Try selecting <strong>All Options</strong> or searching for a different route.</p>
                <button class="btn-reset-filters" onclick="filterTransportCategory('all')">Show All Options</button>
            </div>
        `;
        return;
    }

    const catIcons = {
        bus: '🚌',
        train: '🚆',
        flight: '✈️',
        taxi: '🚖',
        car_rental: '🚗',
        tempo_traveller: '🚐',
        private_coach: '🛋️'
    };

    const catLabels = {
        bus: 'Intercity Bus',
        train: 'Indian Railways',
        flight: 'Domestic Flight',
        taxi: 'Outstation Cab',
        car_rental: 'Self-Drive Rental',
        tempo_traveller: 'Tempo Traveller (Tourist)',
        private_coach: 'Private Luxury Coach'
    };

    grid.innerHTML = options.map(opt => {
        const icon = catIcons[opt.category] || '🚗';
        const catLabel = catLabels[opt.category] || opt.category;

        // Status badge styling
        let statusBadgeClass = 'badge-verified';
        let statusText = 'Partner Verified';
        if (opt.status === 'awaiting_partner_credentials') {
            statusBadgeClass = 'badge-awaiting';
            statusText = 'Awaiting API Credentials';
        } else if (opt.status === 'direct_route_ready' || opt.status === 'active') {
            statusBadgeClass = 'badge-active';
            statusText = 'Direct Route Ready';
        }

        // Amenities chips
        const amenitiesHtml = (opt.amenities || []).slice(0, 4).map(a =>
            `<span class="amenity-chip">✓ ${escapeHtml(a)}</span>`
        ).join('');

        // Price formatting
        let priceDisplay = opt.price_range || '';
        if (opt.price_estimate_inr) {
            priceDisplay = `₹${opt.price_estimate_inr.toLocaleString('en-IN')}`;
        }

        // Capacity
        const capacityHtml = opt.capacity ? `<span class="opt-capacity">👥 ${opt.capacity} Seats</span>` : '';

        // Duration & Timing
        const timingHtml = opt.duration_str ? `<span class="opt-duration">⏱ ${escapeHtml(opt.duration_str)}</span>` : '';

        // Neon DB details & direct call button
        const isNeon = opt.details?.is_neon_registered || (opt.source && opt.source.includes('Neon DB'));
        const phone = opt.details?.contact_phone;
        const rating = opt.details?.rating;
        const neonFlagHtml = isNeon ? `<div class="neon-verified-flag">🏢 Neon DB Verified · ⭐ ${rating || '4.8'} Verified Operator</div>` : '';
        const callBtnHtml = phone ? `
            <a href="tel:${escapeHtml(phone)}" class="tcard-contact-btn" title="Call operator directly">
                📞 Call Operator
            </a>
        ` : '';

        return `
            <div class="transport-card ${opt.category === 'tempo_traveller' ? 'card-tempo' : ''} ${isNeon ? 'card-neon-registered' : ''}">
                <div class="tcard-top">
                    <div class="tcard-badge-row">
                        <span class="tcard-cat"><span class="cat-emoji">${icon}</span> ${catLabel}</span>
                        <span class="tcard-status ${statusBadgeClass}">${statusText}</span>
                    </div>
                    <h3 class="tcard-title">${escapeHtml(opt.title)}</h3>
                    <div class="tcard-operator">${escapeHtml(opt.operator || opt.provider_name || '')}</div>
                    ${neonFlagHtml}
                </div>

                <div class="tcard-body">
                    <div class="tcard-vehicle">
                        <span class="vlabel">Vehicle / Class:</span>
                        <span class="vname">${escapeHtml(opt.vehicle_type || 'Standard')}</span>
                    </div>

                    <div class="tcard-meta-row">
                        ${capacityHtml}
                        ${timingHtml}
                    </div>

                    ${opt.notes ? `<p class="tcard-notes">${escapeHtml(opt.notes)}</p>` : ''}

                    ${amenitiesHtml ? `<div class="tcard-amenities">${amenitiesHtml}</div>` : ''}
                </div>

                <div class="tcard-footer">
                    <div class="tcard-price-col">
                        <span class="price-label">Fare Estimate:</span>
                        <span class="price-val">${priceDisplay || 'Check with Operator'}</span>
                    </div>

                    <div style="display:flex; gap:8px; align-items:center;">
                        ${callBtnHtml}
                        <button class="btn-plan-with-transport" onclick="planTripWithTransport('${escapeJs(opt.title)}', '${opt.category}', '${escapeJs(opt.vehicle_type || '')}')">
                            <span>Plan Trip with AI</span>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <div class="tcard-source-bar">
                    <span>Source: ${escapeHtml(opt.source || 'Verified Partner Network')}</span>
                </div>
            </div>
        `;
    }).join('');
}

function planTripWithTransport(title, category, vehicleType) {
    const origin = State.transport.currentOrigin || 'Delhi';
    const dest = State.transport.currentDest || 'Jaipur';
    const prompt = `I am planning a trip from ${origin} to ${dest} traveling via ${title} (${vehicleType || category}). Please give me a complete itinerary, best departure timing, recommended en-route stops, and top places to visit.`;

    startChat(prompt);
}

// Leaflet Map & Route Visualizer
async function loadRouteOnMap(origin, dest) {
    try {
        const routeResp = await fetch(`/api/transport/route?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(dest)}`);
        const routeData = await routeResp.json();

        if (!routeData || !routeData.route) return;

        const r = routeData.route;
        State.transport.routeSummary = r;

        // Update Ribbon
        const elRoute = document.getElementById('metricRoute');
        const elDist = document.getElementById('metricDistance');
        const elDur = document.getElementById('metricDuration');
        const elEngine = document.getElementById('metricEngine');
        const elHubs = document.getElementById('metricHubs');

        if (elRoute) elRoute.textContent = `${r.origin_name} ➔ ${r.destination_name}`;
        if (elDist) elDist.textContent = `${r.distance_km} km`;
        if (elDur) elDur.textContent = r.duration_str;
        if (elEngine) elEngine.textContent = r.routing_engine || 'MapTiler Routing';

        if (elHubs && r.waypoints && r.waypoints.length >= 2) {
            elHubs.textContent = `${r.waypoints[0].name} ➔ ${r.waypoints[1].name}`;
        }

        // Initialize Leaflet Map if needed
        if (!State.transport.map && typeof L !== 'undefined') {
            const mapConfigResp = await fetch('/api/transport/map-config');
            const mapConfig = await mapConfigResp.json();
            State.transport.mapConfig = mapConfig;

            const map = L.map('transportMap', {
                center: [22.0, 78.0],
                zoom: 5,
                zoomControl: true
            });

            L.tileLayer(mapConfig.tile_url, {
                attribution: mapConfig.attribution,
                maxZoom: 19
            }).addTo(map);

            const attrEl = document.getElementById('mapAttributionText');
            if (attrEl) {
                if (mapConfig.provider === 'openstreetmap') {
                    attrEl.textContent = 'OpenStreetMap & OSRM Driving Navigation';
                } else {
                    attrEl.textContent = 'MapTiler & OpenStreetMap Interactive Navigation';
                }
            }

            State.transport.map = map;
            State.transport.routeLayer = L.layerGroup().addTo(map);
            State.transport.markersLayer = L.layerGroup().addTo(map);
        }

        if (State.transport.map && r.geometry_geojson && r.geometry_geojson.coordinates) {
            State.transport.routeLayer.clearLayers();
            State.transport.markersLayer.clearLayers();

            // Convert GeoJSON [lon, lat] coordinates to Leaflet [lat, lon]
            const latLngs = r.geometry_geojson.coordinates.map(coord => [coord[1], coord[0]]);

            // Outer route glow
            L.polyline(latLngs, {
                color: '#00D2FF',
                weight: 7,
                opacity: 0.45,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(State.transport.routeLayer);

            // Core route line
            const routePolyline = L.polyline(latLngs, {
                color: '#0066FF',
                weight: 4,
                opacity: 0.95,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(State.transport.routeLayer);

            // Origin marker
            if (r.origin_coords) {
                const originIcon = L.divIcon({
                    className: 'custom-map-marker marker-origin',
                    html: '<div class="marker-dot-pulse"></div><div class="marker-pin">📍</div>',
                    iconSize: [32, 32],
                    iconAnchor: [16, 28]
                });
                const originMarker = L.marker([r.origin_coords.lat, r.origin_coords.lon], { icon: originIcon });
                originMarker.bindPopup(`<strong>${escapeHtml(r.origin_name)}</strong><br>${escapeHtml(r.waypoints?.[0]?.name || 'Origin Departure Hub')}`);
                originMarker.addTo(State.transport.markersLayer);
            }

            // Destination marker
            if (r.destination_coords) {
                const destIcon = L.divIcon({
                    className: 'custom-map-marker marker-dest',
                    html: '<div class="marker-dot-pulse dest-pulse"></div><div class="marker-pin">🏁</div>',
                    iconSize: [32, 32],
                    iconAnchor: [16, 28]
                });
                const destMarker = L.marker([r.destination_coords.lat, r.destination_coords.lon], { icon: destIcon });
                destMarker.bindPopup(`<strong>${escapeHtml(r.destination_name)}</strong><br>${escapeHtml(r.waypoints?.[1]?.name || 'Destination Terminal')}`);
                destMarker.addTo(State.transport.markersLayer);
            }

            // Fit bounds
            State.transport.map.fitBounds(routePolyline.getBounds(), {
                padding: [40, 40],
                maxZoom: 12
            });

            setTimeout(() => {
                State.transport.map.invalidateSize();
            }, 250);
        }

    } catch (err) {
        console.error('[Transport] Failed to load route on map:', err);
    }
}

// GTFS Feeds & Public Transit Catalog
async function toggleGtfsFeedsTab() {
    const drawer = document.getElementById('gtfsFeedsDrawer');
    if (!drawer) return;

    if (drawer.style.display === 'none' || !drawer.style.display) {
        drawer.style.display = 'block';
        await loadGtfsFeeds();
        drawer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        drawer.style.display = 'none';
    }
}

function hideGtfsFeedsTab() {
    const drawer = document.getElementById('gtfsFeedsDrawer');
    if (drawer) drawer.style.display = 'none';
}

// API Matrix Modal & Live Availability Matrix
async function toggleApiMatrixModal() {
    const drawer = document.getElementById('apiMatrixDrawer');
    if (!drawer) return;

    if (drawer.style.display === 'none' || !drawer.style.display) {
        drawer.style.display = 'block';
        await loadApiAvailabilityMatrix();
        drawer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        drawer.style.display = 'none';
    }
}

async function loadApiAvailabilityMatrix() {
    const tableBody = document.getElementById('matrixTableBody');
    const summaryChips = document.getElementById('matrixSummaryChips');
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 24px; color:#64748B;">Auditing live integrations and credentials...</td></tr>';

    try {
        const resp = await fetch('/api/transport/availability');
        const data = await resp.json();

        if (summaryChips && data.summary) {
            summaryChips.innerHTML = `
                <span class="matrix-chip matrix-chip-ready">✅ Ready (Credentials Valid): ${data.summary.READY || 0}</span>
                <span class="matrix-chip matrix-chip-public">🌐 Public (No Key Required): ${data.summary.PUBLIC || 0}</span>
                <span class="matrix-chip matrix-chip-missing">⚠️ Missing Credentials: ${data.summary.MISSING_CREDENTIALS || 0}</span>
                <span class="matrix-chip matrix-chip-partner">🤝 Commercial Partner Required: ${data.summary.PARTNER_REQUIRED || 0}</span>
                <span class="matrix-chip" style="background:#F1F5F9; color:#334155;">Total Evaluated: ${data.total_services || 13}</span>
            `;
        }

        const services = data.integrations || [];
        tableBody.innerHTML = services.map(s => {
            const statusClass = `status-badge status-badge-${(s.status || '').toLowerCase()}`;
            return `
                <tr>
                    <td><strong>${escapeHtml(s.service)}</strong></td>
                    <td><span style="font-size:0.82rem; color:#64748B;">${escapeHtml(s.category)}</span></td>
                    <td><span class="${statusClass}">${escapeHtml(s.status)}</span></td>
                    <td><code>${escapeHtml(s.integration_type)}</code></td>
                    <td style="font-size:0.82rem; line-height:1.4;">${escapeHtml(s.notes)}</td>
                </tr>
            `;
        }).join('');

    } catch (err) {
        console.error('[Transport] Matrix fetch error:', err);
        tableBody.innerHTML = '<tr><td colspan="5" style="color:#EF4444; text-align:center; padding: 18px;">Failed to fetch live API matrix.</td></tr>';
    }
}

async function loadGtfsFeeds() {
    const grid = document.getElementById('gtfsFeedsGrid');
    if (!grid) return;

    grid.innerHTML = '<div class="feeds-loading">Loading public GTFS datasets from India GTFS &amp; Mobility Database...</div>';

    try {
        const resp = await fetch('/api/transport/feeds');
        const data = await resp.json();

        const gtfsFeeds = data.india_gtfs_feeds || [];
        const mobCatalog = data.mobility_database_feeds || data.mobility_database_catalog || [];

        if (!gtfsFeeds.length && !mobCatalog.length) {
            grid.innerHTML = '<div class="feeds-error">Could not retrieve feeds catalog.</div>';
            return;
        }

        const feedsHtml = gtfsFeeds.map(f => `
            <div class="feed-card">
                <div class="feed-card-header">
                    <span class="feed-agency-badge">${escapeHtml(f.id || f.agency_id || f.agency_name || f.agency || '')}</span>
                    <span class="feed-badge-static">GTFS ${f.has_realtime ? 'Static + RT' : 'Static'}</span>
                </div>
                <h4 class="feed-title">${escapeHtml(f.agency_name || f.name || f.agency || 'Transit Feed')}</h4>
                <div class="feed-city">📍 ${escapeHtml(f.city || 'India')}, ${escapeHtml(f.state || 'India')}</div>
                <p class="feed-desc">${escapeHtml(f.source || 'Public transit routes, stops and schedules via official open data portal')}</p>
                <div class="feed-meta">
                    <span>License: ${escapeHtml(f.license || 'Open Data')}</span>
                    <span>Updated: ${escapeHtml(f.last_updated || 'Active Open Data')}</span>
                </div>
            </div>
        `).join('');

        const mobHtml = mobCatalog.slice(0, 3).map(m => `
            <div class="feed-card feed-card-mob">
                <div class="feed-card-header">
                    <span class="feed-agency-badge mob-badge">Mobility Database</span>
                    <span class="feed-badge-static">Catalog Registry</span>
                </div>
                <h4 class="feed-title">${escapeHtml(m.feed_name || m.source_name || 'Transit Feed')}</h4>
                <div class="feed-city">📍 India · Global Transit Standard</div>
                <p class="feed-desc">Public transport feed registered with the open Mobility Database catalog.</p>
                <div class="feed-meta">
                    <span>Provider: ${escapeHtml(m.provider || 'Public Transit')}</span>
                    <a href="https://mobilitydatabase.org" target="_blank" rel="noopener">Explore Dataset ↗</a>
                </div>
            </div>
        `).join('');

        grid.innerHTML = feedsHtml + mobHtml;

    } catch (err) {
        console.error('[Transport] Feeds fetch error:', err);
        grid.innerHTML = '<div class="feeds-error">Failed to load GTFS feed directory.</div>';
    }
}

// ============================================================
// NAVBAR
// ============================================================

function initNavbar() {
    const navbar = document.getElementById('navbar');
    const hamburger = document.getElementById('navHamburger');
    const navLinks = document.getElementById('navLinks');

    // Scroll effect
    window.addEventListener('scroll', () => {
        if (window.scrollY > 20) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Hamburger menu
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            navLinks.classList.toggle('open');
        });

        // Close on link click
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => navLinks.classList.remove('open'));
        });
    }
}

// ============================================================
// SCROLL REVEAL ANIMATIONS
// ============================================================

function initScrollReveal() {
    const targets = document.querySelectorAll('.dest-card, .feature-card, .section-header');
    targets.forEach(el => el.classList.add('reveal'));

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        targets.forEach(el => observer.observe(el));
    } else {
        // Fallback: show all
        targets.forEach(el => el.classList.add('visible'));
    }
}

// ============================================================
// PARTICLES (lightweight, CSS-only approach using JS)
// ============================================================

function initParticles() {
    const container = document.getElementById('heroParticles');
    if (!container) return;

    const count = 12;
    const icons = ['✈', '🌍', '🗺', '🏔', '🏖', '⛰', '🌴', '🌊'];

    for (let i = 0; i < count; i++) {
        const p = document.createElement('div');
        p.style.cssText = `
            position: absolute;
            font-size: ${Math.random() * 14 + 10}px;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            opacity: ${Math.random() * 0.2 + 0.05};
            animation: floatSlow ${Math.random() * 8 + 6}s ease-in-out infinite ${Math.random() * 4}s;
            pointer-events: none;
            user-select: none;
        `;
        p.textContent = icons[Math.floor(Math.random() * icons.length)];
        container.appendChild(p);
    }
}

// ============================================================
// SMOOTH SCROLL FOR ANCHOR LINKS
// ============================================================

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            const id = a.getAttribute('href').slice(1);
            if (!id) return;
            const target = document.getElementById(id);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// ============================================================
// BOOT
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    initNavbar();
    initInputHandlers();
    initScrollReveal();
    initParticles();
    initSmoothScroll();
    checkHealth();

    console.log('[YatraPilot AI] Initialized — Premium UI + Agora Voice Ready');
});
