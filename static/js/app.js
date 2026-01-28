/**
 * Mithunam AI Chat Application
 * Main Application Logic
 */

// ============================================
// Configuration & Constants
// ============================================
const API_BASE = '/api';
const STORAGE_KEYS = {
    TOKEN: 'mithunam_chat_token',
    REFRESH_TOKEN: 'mithunam_chat_refresh_token',
    USER: 'mithunam_chat_user',
    THEME: 'mithunam_chat_theme'
};

// ============================================
// State Management
// ============================================
const AppState = {
    user: null,
    token: null,
    currentConversation: null,
    conversations: [],
    isLoading: false,
    isSending: false
};

// ============================================
// API Client
// ============================================
const api = {
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (AppState.token) {
            headers['Authorization'] = `Bearer ${AppState.token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    // Token expired, logout
                    Auth.logout();
                }
                throw new Error(data.error || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },

    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
};

// ============================================
// Authentication Module
// ============================================
const Auth = {
    init() {
        const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
        const userStr = localStorage.getItem(STORAGE_KEYS.USER);

        if (token && userStr) {
            try {
                AppState.token = token;
                AppState.user = JSON.parse(userStr);
                return true;
            } catch (e) {
                this.logout();
            }
        }
        return false;
    },

    async register(email, password, name) {
        try {
            const data = await api.post('/auth/register', { email, password, name });
            this.setSession(data);
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    },

    async login(email, password) {
        try {
            const data = await api.post('/auth/login', { email, password });
            this.setSession(data);
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    },

    setSession(data) {
        AppState.token = data.access_token;
        AppState.user = data.user;
        localStorage.setItem(STORAGE_KEYS.TOKEN, data.access_token);
        localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user));
    },

    logout() {
        AppState.token = null;
        AppState.user = null;
        AppState.currentConversation = null;
        AppState.conversations = [];
        localStorage.removeItem(STORAGE_KEYS.TOKEN);
        localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
        localStorage.removeItem(STORAGE_KEYS.USER);
        Router.navigate('login');
    },

    isAuthenticated() {
        return !!AppState.token && !!AppState.user;
    },

    async updateOnboarding(preferences) {
        try {
            const data = await api.put('/auth/onboarding', { preferences });
            AppState.user = data.user;
            localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user));
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
};

// ============================================
// Router
// ============================================
const Router = {
    routes: {
        'login': 'renderLogin',
        'register': 'renderRegister',
        'onboarding': 'renderOnboarding',
        'chat': 'renderChat',
        'dashboard': 'renderDashboard'
    },

    currentRoute: null,

    init() {
        window.addEventListener('hashchange', () => this.handleRoute());
        this.handleRoute();
    },

    navigate(route) {
        window.location.hash = route;
    },

    handleRoute() {
        const hash = window.location.hash.slice(1) || 'login';

        // Auth guard
        const publicRoutes = ['login', 'register'];
        if (!publicRoutes.includes(hash) && !Auth.isAuthenticated()) {
            this.navigate('login');
            return;
        }

        // Redirect authenticated users away from auth pages
        if (publicRoutes.includes(hash) && Auth.isAuthenticated()) {
            // Check if onboarding is needed
            if (!AppState.user.preferences || Object.keys(AppState.user.preferences).length === 0) {
                this.navigate('onboarding');
                return;
            }
            this.navigate('chat');
            return;
        }

        this.currentRoute = hash;
        const renderMethod = this.routes[hash];

        if (renderMethod && typeof UI[renderMethod] === 'function') {
            UI[renderMethod]();
        } else {
            UI.renderChat();
        }
    }
};

// ============================================
// UI Rendering
// ============================================
const UI = {
    app: null,

    init() {
        this.app = document.getElementById('app');
    },

    // ----- Auth Views -----
    renderLogin() {
        this.app.innerHTML = `
            <div class="auth-container">
                <div class="auth-card">
                    <div class="auth-header">
                        <div class="auth-logo">✨</div>
                        <h1 class="auth-title">Welcome Back</h1>
                        <p class="auth-subtitle">Sign in to continue to Mithunam Chat</p>
                    </div>
                    <form class="auth-form" id="loginForm">
                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-input" id="loginEmail" 
                                   placeholder="your@email.com" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" class="form-input" id="loginPassword" 
                                   placeholder="••••••••" required>
                        </div>
                        <button type="submit" class="btn btn-primary" style="width: 100%;">
                            Sign In
                        </button>
                        <div id="loginError" class="text-center mt-2" style="color: var(--color-error); display: none;"></div>
                    </form>
                    <p class="auth-footer">
                        Don't have an account? <a href="#register">Sign up</a>
                    </p>
                </div>
            </div>
        `;

        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            const errorEl = document.getElementById('loginError');

            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.textContent = 'Signing in...';

            const result = await Auth.login(email, password);

            if (result.success) {
                Router.handleRoute();
            } else {
                errorEl.textContent = result.error;
                errorEl.style.display = 'block';
                btn.disabled = false;
                btn.textContent = 'Sign In';
            }
        });
    },

    renderRegister() {
        this.app.innerHTML = `
            <div class="auth-container">
                <div class="auth-card">
                    <div class="auth-header">
                        <div class="auth-logo">✨</div>
                        <h1 class="auth-title">Create Account</h1>
                        <p class="auth-subtitle">Start your AI conversation journey</p>
                    </div>
                    <form class="auth-form" id="registerForm">
                        <div class="form-group">
                            <label class="form-label">Full Name</label>
                            <input type="text" class="form-input" id="registerName" 
                                   placeholder="John Doe" required minlength="2">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-input" id="registerEmail" 
                                   placeholder="your@email.com" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" class="form-input" id="registerPassword" 
                                   placeholder="••••••••" required minlength="6">
                        </div>
                        <button type="submit" class="btn btn-primary" style="width: 100%;">
                            Create Account
                        </button>
                        <div id="registerError" class="text-center mt-2" style="color: var(--color-error); display: none;"></div>
                    </form>
                    <p class="auth-footer">
                        Already have an account? <a href="#login">Sign in</a>
                    </p>
                </div>
            </div>
        `;

        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('registerName').value;
            const email = document.getElementById('registerEmail').value;
            const password = document.getElementById('registerPassword').value;
            const errorEl = document.getElementById('registerError');

            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.textContent = 'Creating account...';

            const result = await Auth.register(email, password, name);

            if (result.success) {
                Router.navigate('onboarding');
            } else {
                errorEl.textContent = result.error;
                errorEl.style.display = 'block';
                btn.disabled = false;
                btn.textContent = 'Create Account';
            }
        });
    },

    renderOnboarding() {
        const interests = [
            { id: 'coding', icon: '💻', label: 'Coding' },
            { id: 'writing', icon: '✍️', label: 'Writing' },
            { id: 'research', icon: '🔬', label: 'Research' },
            { id: 'business', icon: '📊', label: 'Business' },
            { id: 'creative', icon: '🎨', label: 'Creative' },
            { id: 'learning', icon: '📚', label: 'Learning' },
            { id: 'productivity', icon: '⚡', label: 'Productivity' },
            { id: 'data', icon: '📈', label: 'Data Analysis' },
            { id: 'general', icon: '💬', label: 'General Chat' }
        ];

        this.app.innerHTML = `
            <div class="onboarding-container">
                <div class="onboarding-card">
                    <div class="onboarding-progress">
                        <div class="progress-step active"></div>
                        <div class="progress-step"></div>
                    </div>
                    <div class="onboarding-header">
                        <h1 class="onboarding-title">Welcome, ${AppState.user?.name}! 👋</h1>
                        <p class="onboarding-subtitle">What would you like to use Mithunam Chat for?</p>
                    </div>
                    <div class="interests-grid" id="interestsGrid">
                        ${interests.map(i => `
                            <div class="interest-item" data-id="${i.id}">
                                <div class="interest-icon">${i.icon}</div>
                                <div class="interest-label">${i.label}</div>
                            </div>
                        `).join('')}
                    </div>
                    <button class="btn btn-primary" style="width: 100%;" id="onboardingContinue" disabled>
                        Continue to Chat
                    </button>
                </div>
            </div>
        `;

        const selectedInterests = new Set();
        const items = document.querySelectorAll('.interest-item');
        const continueBtn = document.getElementById('onboardingContinue');

        items.forEach(item => {
            item.addEventListener('click', () => {
                const id = item.dataset.id;
                if (selectedInterests.has(id)) {
                    selectedInterests.delete(id);
                    item.classList.remove('selected');
                } else {
                    selectedInterests.add(id);
                    item.classList.add('selected');
                }
                continueBtn.disabled = selectedInterests.size === 0;
            });
        });

        continueBtn.addEventListener('click', async () => {
            continueBtn.disabled = true;
            continueBtn.textContent = 'Setting up...';

            const result = await Auth.updateOnboarding({
                interests: Array.from(selectedInterests),
                onboardedAt: new Date().toISOString()
            });

            if (result.success) {
                Router.navigate('chat');
            } else {
                Toast.show('Failed to save preferences', 'error');
                continueBtn.disabled = false;
                continueBtn.textContent = 'Continue to Chat';
            }
        });
    },

    // ----- Main App Views -----
    renderChat() {
        this.renderAppLayout('chat');
        Chat.init();
    },

    renderDashboard() {
        this.renderAppLayout('dashboard');
        Dashboard.init();
    },

    renderAppLayout(activeView) {
        const user = AppState.user;
        const initials = user?.name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'U';

        this.app.innerHTML = `
            <div class="app-container">
                <div class="sidebar-overlay" id="sidebarOverlay"></div>
                <aside class="sidebar" id="sidebar">
                    <div class="sidebar-header">
                        <div class="logo">
                            <div class="logo-icon">M</div>
                            <span>Mithunam AI</span>
                        </div>
                    </div>
                    <div class="sidebar-content">
                        <button class="btn btn-secondary new-chat-btn" id="newChatBtn">
                            <span>➕</span> New Chat
                        </button>
                        <div class="sidebar-section">
                            <div class="sidebar-section-title">Recent Conversations</div>
                            <div class="conversation-list" id="conversationList">
                                <div class="text-center text-muted" style="padding: 1rem;">
                                    Loading...
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="sidebar-footer">
                        <nav style="margin-bottom: 1rem;">
                            <a href="#chat" class="conversation-item ${activeView === 'chat' ? 'active' : ''}">
                                <span class="conversation-item-icon">💬</span>
                                <span>Chat</span>
                            </a>
                            <a href="#dashboard" class="conversation-item ${activeView === 'dashboard' ? 'active' : ''}">
                                <span class="conversation-item-icon">📊</span>
                                <span>Dashboard</span>
                            </a>
                        </nav>
                        <div class="user-profile dropdown" id="userDropdown">
                            <div class="user-avatar">${initials}</div>
                            <div class="user-info">
                                <div class="user-name">${user?.name || 'User'}</div>
                                <div class="user-email">${user?.email || ''}</div>
                            </div>
                            <span>▼</span>
                            <div class="dropdown-menu">
                                <div class="dropdown-item" onclick="ThemeToggle.toggle()">
                                    <span>🌓</span> Toggle Theme
                                </div>
                                <div class="dropdown-item danger" onclick="Auth.logout()">
                                    <span>🚪</span> Sign Out
                                </div>
                            </div>
                        </div>
                    </div>
                </aside>
                <main class="main-content">
                    <header class="main-header">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <button class="btn btn-ghost btn-icon" id="menuToggle" style="display: none;">
                                ☰
                            </button>
                            <h1 class="header-title" id="headerTitle">
                                ${activeView === 'dashboard' ? 'Dashboard' : 'New Chat'}
                            </h1>
                        </div>
                        <div class="header-actions">
                            <button class="btn btn-ghost btn-icon" onclick="ThemeToggle.toggle()" title="Toggle theme">
                                🌓
                            </button>
                        </div>
                    </header>
                    <div id="mainView">
                        <!-- Content injected here -->
                    </div>
                </main>
            </div>
            <div class="toast-container" id="toastContainer"></div>
        `;

        // Setup sidebar interactions
        this.setupSidebar();

        // Load conversations
        Chat.loadConversations();
    },

    setupSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        const menuToggle = document.getElementById('menuToggle');
        const userDropdown = document.getElementById('userDropdown');

        // Mobile menu toggle
        if (window.innerWidth <= 768) {
            menuToggle.style.display = 'flex';
        }

        menuToggle?.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        });

        overlay?.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });

        // User dropdown
        userDropdown?.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('active');
        });

        document.addEventListener('click', () => {
            userDropdown?.classList.remove('active');
        });

        // New chat button
        document.getElementById('newChatBtn')?.addEventListener('click', () => {
            Chat.startNewChat();
        });

        // Responsive
        window.addEventListener('resize', () => {
            if (window.innerWidth <= 768) {
                menuToggle.style.display = 'flex';
            } else {
                menuToggle.style.display = 'none';
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
            }
        });
    }
};

// ============================================
// Chat Module
// ============================================
const Chat = {
    init() {
        const mainView = document.getElementById('mainView');
        mainView.innerHTML = `
            <div class="chat-container">
                <div class="chat-messages" id="chatMessages">
                    <div class="empty-state" id="emptyState">
                        <div class="empty-state-icon">✨</div>
                        <h3 class="empty-state-title">Start a New Conversation</h3>
                        <p class="empty-state-text">
                            Ask me anything! I can help with coding, writing, research, 
                            or even real-time information like weather and prices.
                        </p>
                        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center;">
                            <button class="btn btn-secondary" onclick="Chat.sendQuickMessage('What is the current price of Bitcoin?')">
                                💰 Bitcoin Price
                            </button>
                            <button class="btn btn-secondary" onclick="Chat.sendQuickMessage('What\\'s the weather like in Mumbai?')">
                                ⛅ Weather
                            </button>
                            <button class="btn btn-secondary" onclick="Chat.sendQuickMessage('Explain quantum computing in simple terms')">
                                🔬 Learn Something
                            </button>
                        </div>
                    </div>
                </div>
                <div class="chat-input-container">
                    <div class="chat-input-wrapper">
                        <textarea class="chat-input" id="chatInput" 
                                  placeholder="Ask me anything..." 
                                  rows="1"></textarea>
                        <button class="send-btn" id="sendBtn" disabled>
                            ➤
                        </button>
                    </div>
                    <p class="text-muted text-center mt-2" style="font-size: 0.75rem;">
                        Powered by Mithunam AI • Real-time data enabled
                    </p>
                </div>
            </div>
        `;

        this.setupInput();

        // Load current conversation if exists
        if (AppState.currentConversation) {
            this.loadConversation(AppState.currentConversation.id);
        }
    },

    setupInput() {
        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');

        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 200) + 'px';
            sendBtn.disabled = !input.value.trim();
        });

        // Send on Enter (Shift+Enter for new line)
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (input.value.trim()) {
                    this.sendMessage(input.value.trim());
                }
            }
        });

        // Send button click
        sendBtn.addEventListener('click', () => {
            if (input.value.trim()) {
                this.sendMessage(input.value.trim());
            }
        });
    },

    sendQuickMessage(message) {
        this.sendMessage(message);
    },

    async sendMessage(message) {
        if (AppState.isSending) return;

        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const messagesContainer = document.getElementById('chatMessages');

        // Hide empty state
        document.getElementById('emptyState')?.remove();

        // Clear input
        input.value = '';
        input.style.height = 'auto';
        sendBtn.disabled = true;

        // Add user message
        this.addMessage('user', message);

        // Show typing indicator
        const typingId = this.showTypingIndicator();

        AppState.isSending = true;

        try {
            const response = await api.post('/chat/message', {
                message,
                conversation_id: AppState.currentConversation?.id
            });

            // Remove typing indicator
            this.removeTypingIndicator(typingId);

            // Update current conversation
            if (response.conversation) {
                AppState.currentConversation = response.conversation;
                document.getElementById('headerTitle').textContent = response.conversation.title;
                this.loadConversations(); // Refresh list
            }

            // Add AI response
            this.addMessage('assistant', response.message.content, response.search_used);

        } catch (error) {
            this.removeTypingIndicator(typingId);
            Toast.show(error.message || 'Failed to send message', 'error');
        } finally {
            AppState.isSending = false;
        }
    },

    addMessage(role, content, searchUsed = false) {
        const container = document.getElementById('chatMessages');
        const avatar = role === 'assistant' ? '✨' :
            (AppState.user?.name?.[0]?.toUpperCase() || 'U');

        const messageEl = document.createElement('div');
        messageEl.className = `message ${role}`;

        // Parse markdown-like formatting
        const formattedContent = this.formatContent(content);

        messageEl.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${formattedContent}</div>
                <div class="message-meta">
                    <span>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    ${searchUsed ? '<span class="search-indicator">🔍 Real-time data</span>' : ''}
                </div>
            </div>
        `;

        container.appendChild(messageEl);
        container.scrollTop = container.scrollHeight;
    },

    formatContent(content) {
        // Simple markdown-like formatting
        let formatted = content
            // Escape HTML
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            // Code blocks
            .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
            // Inline code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Bold
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            // Line breaks
            .replace(/\n/g, '<br>');

        return formatted;
    },

    showTypingIndicator() {
        const container = document.getElementById('chatMessages');
        const id = 'typing-' + Date.now();

        const el = document.createElement('div');
        el.id = id;
        el.className = 'message assistant';
        el.innerHTML = `
            <div class="message-avatar">✨</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        container.appendChild(el);
        container.scrollTop = container.scrollHeight;

        return id;
    },

    removeTypingIndicator(id) {
        document.getElementById(id)?.remove();
    },

    async loadConversations() {
        try {
            const data = await api.get('/chat/conversations');
            AppState.conversations = data.conversations;
            this.renderConversationList();
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    },

    renderConversationList() {
        const list = document.getElementById('conversationList');
        if (!list) return;

        if (AppState.conversations.length === 0) {
            list.innerHTML = `
                <div class="text-center text-muted" style="padding: 1rem; font-size: 0.875rem;">
                    No conversations yet
                </div>
            `;
            return;
        }

        list.innerHTML = AppState.conversations.map(conv => `
            <div class="conversation-item ${AppState.currentConversation?.id === conv.id ? 'active' : ''}" 
                 data-id="${conv.id}">
                <span class="conversation-item-icon">💬</span>
                <div class="conversation-item-content">
                    <div class="conversation-item-title">${this.escapeHtml(conv.title)}</div>
                    <div class="conversation-item-time">${conv.message_count} messages</div>
                </div>
            </div>
        `).join('');

        // Add click handlers
        list.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.dataset.id;  // Keep as string for MongoDB ObjectId
                this.loadConversation(id);
            });
        });
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    async loadConversation(id) {
        // Ensure we are in chat view
        if (window.location.hash !== '#chat') {
            Router.navigate('chat');
            // Wait for view to render
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        try {
            const data = await api.get(`/chat/conversations/${id}`);
            AppState.currentConversation = data.conversation;

            // Update UI
            document.getElementById('headerTitle').textContent = data.conversation.title;

            // Re-render messages
            const container = document.getElementById('chatMessages');
            container.innerHTML = '';

            if (data.conversation.messages && data.conversation.messages.length > 0) {
                data.conversation.messages.forEach(msg => {
                    this.addMessage(msg.role, msg.content, msg.metadata?.search_used);
                });
            } else {
                container.innerHTML = `
                    <div class="empty-state" id="emptyState">
                        <div class="empty-state-icon">💬</div>
                        <h3 class="empty-state-title">Continue your conversation</h3>
                        <p class="empty-state-text">Pick up where you left off.</p>
                    </div>
                `;
            }

            this.renderConversationList();

        } catch (error) {
            Toast.show('Failed to load conversation', 'error');
        }
    },

    startNewChat() {
        AppState.currentConversation = null;
        document.getElementById('headerTitle').textContent = 'New Chat';

        const container = document.getElementById('chatMessages');
        container.innerHTML = `
            <div class="empty-state" id="emptyState">
                <div class="empty-state-icon">✨</div>
                <h3 class="empty-state-title">Start a New Conversation</h3>
                <p class="empty-state-text">
                    Ask me anything! I can help with coding, writing, research, 
                    or even real-time information like weather and prices.
                </p>
                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center;">
                    <button class="btn btn-secondary" onclick="Chat.sendQuickMessage('What is the current price of Bitcoin?')">
                        💰 Bitcoin Price
                    </button>
                    <button class="btn btn-secondary" onclick="Chat.sendQuickMessage('What\\'s the weather like in Mumbai?')">
                        ⛅ Weather
                    </button>
                    <button class="btn btn-secondary" onclick="Chat.sendQuickMessage('Explain quantum computing in simple terms')">
                        🔬 Learn Something
                    </button>
                </div>
            </div>
        `;

        this.renderConversationList();

        // Close mobile sidebar
        document.getElementById('sidebar').classList.remove('open');
        document.getElementById('sidebarOverlay').classList.remove('active');
    }
};

// ============================================
// Dashboard Module
// ============================================
const Dashboard = {
    chart: null,

    async init() {
        const mainView = document.getElementById('mainView');
        mainView.innerHTML = `
            <div class="dashboard-container">
                <div class="dashboard-header">
                    <h2 class="dashboard-title">Your AI Usage Dashboard</h2>
                    <p class="dashboard-subtitle">Track your conversations and insights</p>
                </div>
                
                <div class="stats-grid" id="statsGrid">
                    <div class="stat-card skeleton" style="height: 100px;"></div>
                    <div class="stat-card skeleton" style="height: 100px;"></div>
                    <div class="stat-card skeleton" style="height: 100px;"></div>
                    <div class="stat-card skeleton" style="height: 100px;"></div>
                </div>
                
                <div class="charts-grid">
                    <div class="chart-card">
                        <div class="chart-header">
                            <h3 class="chart-title">Message Activity</h3>
                        </div>
                        <div class="chart-container">
                            <canvas id="activityChart"></canvas>
                        </div>
                    </div>
                    <div class="chart-card">
                        <div class="chart-header">
                            <h3 class="chart-title">AI Insights</h3>
                        </div>
                        <div id="insightsContainer">
                            <div class="skeleton" style="height: 200px;"></div>
                        </div>
                    </div>
                </div>
                
                <div class="chart-card">
                    <div class="chart-header">
                        <h3 class="chart-title">Recent Conversations</h3>
                    </div>
                    <div id="topicsContainer">
                        <div class="skeleton" style="height: 150px;"></div>
                    </div>
                </div>
            </div>
        `;

        await this.loadData();
    },

    async loadData() {
        try {
            // Load stats
            const [statsData, usageData, insightsData, topicsData] = await Promise.all([
                api.get('/analytics/stats'),
                api.get('/analytics/usage?days=14'),
                api.get('/analytics/insights'),
                api.get('/analytics/topics?limit=5')
            ]);

            this.renderStats(statsData.stats);
            this.renderChart(usageData.usage);
            this.renderInsights(insightsData.insights);
            this.renderTopics(topicsData.topics);

        } catch (error) {
            Toast.show('Failed to load dashboard data', 'error');
        }
    },

    renderStats(stats) {
        const grid = document.getElementById('statsGrid');
        grid.innerHTML = `
            <div class="stat-card">
                <div class="stat-icon">💬</div>
                <div class="stat-content">
                    <div class="stat-value">${stats.total_conversations}</div>
                    <div class="stat-label">Total Conversations</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📝</div>
                <div class="stat-content">
                    <div class="stat-value">${stats.total_messages}</div>
                    <div class="stat-label">Total Messages</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📅</div>
                <div class="stat-content">
                    <div class="stat-value">${stats.messages_today}</div>
                    <div class="stat-label">Messages Today</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🔍</div>
                <div class="stat-content">
                    <div class="stat-value">${stats.search_queries_used}</div>
                    <div class="stat-label">Real-time Queries</div>
                </div>
            </div>
        `;
    },

    renderChart(usage) {
        const ctx = document.getElementById('activityChart');
        if (!ctx) return;

        // Simple chart rendering (without Chart.js for now)
        const data = usage.daily_messages;
        const max = Math.max(...data.map(d => d.count), 1);

        const canvas = ctx;
        const context = canvas.getContext('2d');
        const width = canvas.parentElement.clientWidth;
        const height = 250;

        canvas.width = width;
        canvas.height = height;

        const padding = 40;
        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;
        const barWidth = chartWidth / data.length - 4;

        // Clear
        context.clearRect(0, 0, width, height);

        // Draw bars
        const gradient = context.createLinearGradient(0, chartHeight, 0, 0);
        gradient.addColorStop(0, '#7c3aed');
        gradient.addColorStop(1, '#06b6d4');

        data.forEach((item, i) => {
            const barHeight = (item.count / max) * chartHeight;
            const x = padding + i * (barWidth + 4);
            const y = height - padding - barHeight;

            context.fillStyle = gradient;
            context.beginPath();
            context.roundRect(x, y, barWidth, barHeight, 4);
            context.fill();
        });

        // X axis labels
        context.fillStyle = '#64748b';
        context.font = '10px Inter, sans-serif';
        context.textAlign = 'center';

        data.forEach((item, i) => {
            if (i % 3 === 0) {
                const x = padding + i * (barWidth + 4) + barWidth / 2;
                const label = new Date(item.date).toLocaleDateString('en', { month: 'short', day: 'numeric' });
                context.fillText(label, x, height - 10);
            }
        });
    },

    renderInsights(insights) {
        const container = document.getElementById('insightsContainer');
        container.innerHTML = `
            <div style="display: grid; gap: 1rem;">
                <div class="glass-card" style="padding: 1rem;">
                    <div style="font-size: 0.875rem; color: var(--color-text-muted);">Most Active Hour</div>
                    <div style="font-size: 1.25rem; font-weight: 600;">
                        ${insights.most_active_hour ? `${insights.most_active_hour}:00` : 'N/A'}
                    </div>
                </div>
                <div class="glass-card" style="padding: 1rem;">
                    <div style="font-size: 0.875rem; color: var(--color-text-muted);">Most Active Day</div>
                    <div style="font-size: 1.25rem; font-weight: 600;">
                        ${insights.most_active_day || 'N/A'}
                    </div>
                </div>
                <div class="glass-card" style="padding: 1rem;">
                    <div style="font-size: 0.875rem; color: var(--color-text-muted);">Avg Response Length</div>
                    <div style="font-size: 1.25rem; font-weight: 600;">
                        ${insights.avg_response_length} chars
                    </div>
                </div>
            </div>
        `;
    },

    renderTopics(topics) {
        const container = document.getElementById('topicsContainer');

        if (topics.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="padding: 2rem;">
                    <div class="empty-state-icon" style="width: 48px; height: 48px; font-size: 1.25rem;">💬</div>
                    <p class="text-muted">No conversations yet. Start chatting!</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="conversation-list">
                ${topics.map(topic => `
                    <div class="conversation-item" onclick="Router.navigate('chat'); setTimeout(() => Chat.loadConversation(${topic.id}), 100);">
                        <span class="conversation-item-icon">💬</span>
                        <div class="conversation-item-content">
                            <div class="conversation-item-title">${Chat.escapeHtml(topic.title)}</div>
                            <div class="conversation-item-time">${topic.message_count} messages</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
};

// ============================================
// Toast Notifications
// ============================================
const Toast = {
    show(message, type = 'info') {
        const container = document.getElementById('toastContainer') || this.createContainer();

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '✓',
            error: '✕',
            info: 'ℹ',
            warning: '⚠'
        };

        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
        `;

        container.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'toastSlide 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    },

    createContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }
};

// ============================================
// Theme Toggle
// ============================================
const ThemeToggle = {
    init() {
        const savedTheme = localStorage.getItem(STORAGE_KEYS.THEME);
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        }
    },

    toggle() {
        const current = document.documentElement.getAttribute('data-theme');
        const newTheme = current === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem(STORAGE_KEYS.THEME, newTheme);
    }
};

// ============================================
// App Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    ThemeToggle.init();
    UI.init();
    Auth.init();
    Router.init();
});
