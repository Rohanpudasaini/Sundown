// Sundown Frontend Application
class SundownApp {
    constructor() {
        this.token = null;
        this.user = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordingStartTime = null;
        this.recordingTimer = null;
        
        this.init();
    }
    
    async init() {
        // Check for stored token
        const storedToken = localStorage.getItem('sundown_token');
        if (storedToken) {
            this.token = storedToken;
            await this.validateToken();
        }
        
        this.bindEvents();
        this.showScreen('auth-screen');
    }
    
    bindEvents() {
        // Auth tabs
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchAuthTab(tab.dataset.tab));
        });
        
        // Auth forms
        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('signup-form').addEventListener('submit', (e) => this.handleSignup(e));
        
        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());
        
        // Input method switching
        document.getElementById('text-input-btn').addEventListener('click', () => this.switchInputMethod('text'));
        document.getElementById('voice-input-btn').addEventListener('click', () => this.switchInputMethod('voice'));
        
        // Save entry
        document.getElementById('save-entry-btn').addEventListener('click', () => this.saveEntry());
        
        // Voice recording
        document.getElementById('record-btn').addEventListener('click', () => this.startRecording());
        document.getElementById('stop-btn').addEventListener('click', () => this.stopRecording());
        document.getElementById('re-record-btn').addEventListener('click', () => this.resetVoiceInput());
        document.getElementById('use-transcript-btn').addEventListener('click', () => this.useTranscript());
        
        // Search
        document.getElementById('search-btn').addEventListener('click', () => this.openSearchModal());
        document.getElementById('close-search').addEventListener('click', () => this.closeSearchModal());
        document.getElementById('search-submit').addEventListener('click', () => this.performSearch());
        
        // Modal backdrop click
        document.getElementById('search-modal').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) this.closeSearchModal();
        });
    }
    
    // ===== Auth =====
    switchAuthTab(tab) {
        document.querySelectorAll('.auth-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
        document.querySelectorAll('.auth-form').forEach(f => f.classList.toggle('active', f.id === `${tab}-form`));
    }
    
    async handleLogin(e) {
        e.preventDefault();
        const form = e.target;
        const email = form.email.value;
        const password = form.password.value;
        
        try {
            const response = await this.api('/users/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ username: email, password })
            });
            
            this.token = response.access_token;
            localStorage.setItem('sundown_token', this.token);
            await this.validateToken();
            this.showScreen('main-screen');
            this.loadEntries();
        } catch (err) {
            this.showError('Login failed: ' + err.message);
        }
    }
    
    async handleSignup(e) {
        e.preventDefault();
        const form = e.target;
        const data = {
            username: form.username.value,
            email: form.email.value,
            hashed_password: form.password.value
        };
        
        try {
            await this.api('/users/signup', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            this.showError('Account created! Please sign in.', 'success');
            this.switchAuthTab('login');
            form.reset();
        } catch (err) {
            this.showError('Signup failed: ' + err.message);
        }
    }
    
    async validateToken() {
        try {
            this.user = await this.api('/users/me');
            return true;
        } catch (err) {
            this.token = null;
            localStorage.removeItem('sundown_token');
            return false;
        }
    }
    
    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('sundown_token');
        this.showScreen('auth-screen');
        document.getElementById('login-form').reset();
    }
    
    // ===== Screens =====
    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        document.getElementById(screenId).classList.add('active');
    }
    
    // ===== Input Methods =====
    switchInputMethod(method) {
        document.querySelectorAll('.input-method-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.method === method);
        });
        document.querySelectorAll('.input-area').forEach(area => {
            area.classList.toggle('active', area.id === `${method}-input-area`);
        });
    }
    
    // ===== Entry Management =====
    async saveEntry() {
        const text = document.getElementById('entry-text').value.trim();
        if (!text) {
            this.showError('Please write something first');
            return;
        }
        
        const btn = document.getElementById('save-entry-btn');
        btn.disabled = true;
        btn.textContent = 'Saving...';
        
        try {
            const today = new Date().toISOString().split('T')[0];
            const response = await this.api('/entries/create_entry', {
                method: 'POST',
                body: JSON.stringify({
                    entry_date: today,
                    input_type: 'text',
                    status: 'received',
                    raw_text: text
                })
            });
            
            document.getElementById('entry-text').value = '';
            this.showError('Entry saved! Processing...', 'success');
            this.loadEntries();
            
            // Poll for follow-up questions
            this.pollForFollowUps(response.entry_id);
        } catch (err) {
            this.showError('Failed to save entry: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Save Entry';
        }
    }
    
    async loadEntries() {
        try {
            const data = await this.api('/entries/');
            this.renderEntries(data.results || data);
        } catch (err) {
            console.error('Failed to load entries:', err);
        }
    }
    
    renderEntries(entries) {
        const container = document.getElementById('entries-list');
        
        if (!entries || entries.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
                        <path d="m15 5 4 4"/>
                    </svg>
                    <p>No entries yet. Start your first check-in above!</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = entries.map(entry => this.renderEntryCard(entry)).join('');
    }
    
    renderEntryCard(entry) {
        const date = new Date(entry.entry_date).toLocaleDateString(undefined, { 
            weekday: 'short', 
            month: 'short', 
            day: 'numeric' 
        });
        const mood = entry.extractions?.[0]?.mood || 'pending';
        const topics = entry.extractions?.[0]?.topics?.split(', ').slice(0, 3) || [];
        
        return `
            <article class="entry-card" data-id="${entry.id}">
                <div class="entry-header">
                    <span class="entry-date">${date}</span>
                    <span class="entry-mood">${mood}</span>
                </div>
                <p class="entry-text">${this.escapeHtml(entry.raw_text || 'Voice entry - processing...')}</p>
                <div class="entry-topics">
                    ${topics.map(t => `<span class="topic-tag">${this.escapeHtml(t)}</span>`).join('')}
                </div>
            </article>
        `;
    }
    
    // ===== Voice Recording =====
    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];
            
            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) this.audioChunks.push(e.data);
            };
            
            this.mediaRecorder.onstop = () => this.processRecording();
            
            this.mediaRecorder.start(100); // Collect data every 100ms
            this.recordingStartTime = Date.now();
            
            // UI updates
            document.getElementById('voice-recorder').classList.add('recording');
            document.getElementById('record-btn').classList.add('hidden');
            document.getElementById('stop-btn').classList.remove('hidden');
            document.querySelector('.recording-status').textContent = 'Recording...';
            document.querySelector('.recording-timer').classList.remove('hidden');
            
            // Timer
            this.recordingTimer = setInterval(() => {
                const elapsed = Date.now() - this.recordingStartTime;
                const mins = Math.floor(elapsed / 60000).toString().padStart(2, '0');
                const secs = Math.floor((elapsed % 60000) / 1000).toString().padStart(2, '0');
                document.querySelector('.recording-timer').textContent = `${mins}:${secs}`;
            }, 1000);
            
            // Animate visualizer
            this.animateVisualizer(stream);
            
        } catch (err) {
            this.showError('Microphone access denied: ' + err.message);
        }
    }
    
    animateVisualizer(stream) {
        const audioContext = new AudioContext();
        const analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
        
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        const bars = document.querySelectorAll('.wave-bar');
        
        const animate = () => {
            if (!this.mediaRecorder || this.mediaRecorder.state !== 'recording') return;
            
            analyser.getByteFrequencyData(dataArray);
            
            bars.forEach((bar, i) => {
                const value = dataArray[i * 2] || 0;
                const height = Math.max(10, (value / 255) * 100);
                bar.style.height = `${height}%`;
            });
            
            requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
        
        clearInterval(this.recordingTimer);
        document.getElementById('voice-recorder').classList.remove('recording');
        document.querySelector('.recording-status').textContent = 'Processing...';
        document.querySelector('.recording-timer').classList.add('hidden');
    }
    
    async processRecording() {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        
        try {
            // Upload to MinIO via backend
            const formData = new FormData();
            formData.append('file', audioBlob, `entry-${Date.now()}.webm`);
            
            const uploadResponse = await this.api('/entries/upload-audio', {
                method: 'POST',
                body: formData
            });
            
            // Create entry with audio URL
            const today = new Date().toISOString().split('T')[0];
            const entryResponse = await this.api('/entries/create_entry', {
                method: 'POST',
                body: JSON.stringify({
                    entry_date: today,
                    input_type: 'voice',
                    status: 'transcribing',
                    audio_url: uploadResponse.url
                })
            });
            
            this.showTranscript('Transcribing...', true);
            this.pollForTranscript(entryResponse.entry_id);
            
        } catch (err) {
            this.showError('Failed to process recording: ' + err.message);
            this.resetVoiceInput();
        }
    }
    
    async pollForTranscript(entryId) {
        const poll = async () => {
            try {
                const entry = await this.api(`/entries/${entryId}`);
                if (entry.status === 'transcribed' && entry.raw_text) {
                    this.showTranscript(entry.raw_text);
                } else if (entry.status === 'transcribing') {
                    setTimeout(poll, 2000);
                } else {
                    this.showError('Transcription failed');
                    this.resetVoiceInput();
                }
            } catch (err) {
                setTimeout(poll, 2000);
            }
        };
        poll();
    }
    
    showTranscript(text, loading = false) {
        document.getElementById('voice-recorder').classList.add('hidden');
        document.getElementById('voice-transcript').classList.remove('hidden');
        document.getElementById('transcript-text').value = text;
        document.getElementById('use-transcript-btn').disabled = loading;
        document.getElementById('use-transcript-btn').textContent = loading ? 'Transcribing...' : 'Use This';
    }
    
    async useTranscript() {
        const text = document.getElementById('transcript-text').value;
        if (!text || text === 'Transcribing...') return;
        
        this.switchInputMethod('text');
        document.getElementById('entry-text').value = text;
        this.resetVoiceInput();
    }
    
    resetVoiceInput() {
        this.audioChunks = [];
        this.recordingStartTime = null;
        
        document.getElementById('voice-recorder').classList.remove('hidden', 'recording');
        document.getElementById('voice-transcript').classList.add('hidden');
        document.getElementById('record-btn').classList.remove('hidden');
        document.getElementById('stop-btn').classList.add('hidden');
        document.querySelector('.recording-status').textContent = 'Tap to start recording';
        document.querySelector('.recording-timer').classList.add('hidden');
        document.querySelector('.recording-timer').textContent = '00:00';
        document.querySelectorAll('.wave-bar').forEach(bar => bar.style.height = '10%');
    }
    
    // ===== Follow-up Questions =====
    async pollForFollowUps(entryId) {
        const poll = async () => {
            try {
                const data = await this.api(`/entries/${entryId}/follow_up/questions`);
                if (data.results && data.results.length > 0) {
                    this.renderFollowUps(data.results);
                } else {
                    setTimeout(poll, 3000);
                }
            } catch (err) {
                setTimeout(poll, 3000);
            }
        };
        
        document.getElementById('followup-section').classList.remove('hidden');
        document.getElementById('followup-loading').classList.remove('hidden');
        poll();
    }
    
    renderFollowUps(questions) {
        document.getElementById('followup-loading').classList.add('hidden');
        const container = document.getElementById('followup-questions');
        
        container.innerHTML = questions.map((q, i) => `
            <div class="followup-question" data-id="${q.id}">
                <div class="followup-question-header">
                    <span class="followup-question-number">${i + 1}</span>
                    <span class="followup-question-text">${this.escapeHtml(q.question)}</span>
                </div>
                <textarea class="followup-answer" placeholder="Your thoughts..." data-question-id="${q.id}"></textarea>
            </div>
        `).join('');
        
        // Add save handlers
        container.querySelectorAll('.followup-answer').forEach(textarea => {
            textarea.addEventListener('blur', () => this.saveFollowUpAnswer(textarea));
        });
    }
    
    async saveFollowUpAnswer(textarea) {
        const questionId = textarea.dataset.questionId;
        const answer = textarea.value.trim();
        if (!answer) return;
        
        try {
            await this.api(`/entries/follow_up_questions/${questionId}`, {
                method: 'PATCH',
                body: JSON.stringify({ answer })
            });
        } catch (err) {
            console.error('Failed to save answer:', err);
        }
    }
    
    // ===== Search =====
    openSearchModal() {
        document.getElementById('search-modal').classList.remove('hidden');
        document.getElementById('search-query').focus();
    }
    
    closeSearchModal() {
        document.getElementById('search-modal').classList.add('hidden');
        document.getElementById('search-query').value = '';
        document.getElementById('search-results').innerHTML = '';
    }
    
    async performSearch() {
        const query = document.getElementById('search-query').value.trim();
        const source = document.getElementById('search-source').value;
        
        if (!query) return;
        
        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Searching...</p></div>';
        
        try {
            const data = await this.api(`/entries/search?query=${encodeURIComponent(query)}&source=${source}&limit=10`);
            
            if (!data || data.length === 0) {
                resultsContainer.innerHTML = '<p style="text-align:center;color:var(--color-text-muted);padding:20px;">No results found</p>';
                return;
            }
            
            resultsContainer.innerHTML = data.map(item => this.renderSearchResult(item, source)).join('');
        } catch (err) {
            resultsContainer.innerHTML = `<p style="text-align:center;color:var(--color-danger);padding:20px;">Search failed: ${err.message}</p>`;
        }
    }
    
    renderSearchResult(item, source) {
        let dateStr = '', typeLabel = '', content = '';
        
        switch (source) {
            case 'entries':
                dateStr = new Date(item.date).toLocaleDateString();
                typeLabel = 'Entry';
                content = item.text;
                break;
            case 'extractions':
                dateStr = 'Extraction';
                typeLabel = 'Insight';
                content = `Mood: ${item.mood}, Topics: ${item.topics}`;
                break;
            case 'weekly':
                dateStr = item.week;
                typeLabel = 'Weekly';
                content = item.summary;
                break;
            case 'monthly':
                dateStr = item.month;
                typeLabel = 'Monthly';
                content = item.summary;
                break;
        }
        
        return `
            <div class="search-result-item">
                <div class="search-result-header">
                    <span class="search-result-date">${this.escapeHtml(dateStr)}</span>
                    <span class="search-result-type">${typeLabel}</span>
                </div>
                <p class="search-result-text">${this.escapeHtml(content)}</p>
            </div>
        `;
    }
    
    // ===== API Helper =====
    async api(endpoint, options = {}) {
        const url = `${window.location.origin}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return response.json();
    }
    
    // ===== Utils =====
    showError(message, type = 'error') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            padding: 12px 24px;
            border-radius: var(--radius-md);
            font-weight: 500;
            z-index: 2000;
            animation: slideUp 0.3s ease forwards;
            ${type === 'success' 
                ? 'background: var(--color-success); color: white;' 
                : 'background: var(--color-danger); color: white;'}
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideDown 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Add toast animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        to { transform: translateX(-50%) translateY(0); }
    }
    @keyframes slideDown {
        to { transform: translateX(-50%) translateY(100px); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SundownApp();
});