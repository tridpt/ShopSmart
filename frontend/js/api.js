/**
 * ShopSmart AI — API Client
 */
const API = {
    BASE: '',
    TOKEN_KEY: 'shopsmart_token',

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY) || '';
    },

    setToken(token) {
        if (token) localStorage.setItem(this.TOKEN_KEY, token);
        else localStorage.removeItem(this.TOKEN_KEY);
    },

    _headers(extra = {}) {
        const h = { ...extra };
        const token = this.getToken();
        if (token) h['Authorization'] = `Bearer ${token}`;
        return h;
    },

    _handle401(res) {
        // Token expired/invalid → force re-login.
        if (res.status === 401 && typeof Auth !== 'undefined') {
            Auth.logout();
        }
    },

    async post(endpoint, data) {
        const res = await fetch(`${this.BASE}${endpoint}`, {
            method: 'POST',
            headers: this._headers({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(data),
        });
        this._handle401(res);
        return res.json();
    },

    async get(endpoint) {
        const res = await fetch(`${this.BASE}${endpoint}`, {
            headers: this._headers(),
        });
        this._handle401(res);
        return res.json();
    },

    async del(endpoint) {
        const res = await fetch(`${this.BASE}${endpoint}`, {
            method: 'DELETE',
            headers: this._headers(),
        });
        this._handle401(res);
        return res.json();
    },

    async put(endpoint, data) {
        const res = await fetch(`${this.BASE}${endpoint}`, {
            method: 'PUT',
            headers: this._headers({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(data),
        });
        this._handle401(res);
        return res.json();
    },

    // Auth
    register: (email, password, display_name) => API.post('/api/auth/register', { email, password, display_name }),
    loginUser: (email, password) => API.post('/api/auth/login', { email, password }),
    getMe: () => API.get('/api/auth/me'),
    updateSettings: (settings) => API.put('/api/auth/settings', settings),

    // Convenience methods
    sendMessage: (message) => API.post('/api/chat', { message }),
    getChatHistory: () => API.get('/api/chat/history'),
    clearChat: () => API.post('/api/chat/clear'),
    getTracked: () => API.get('/api/tracked'),
    deleteTracked: (id) => API.del(`/api/tracked/${id}`),
    updateTarget: (id, price) => API.put(`/api/tracked/${id}/target`, { target_price: price }),
    getPriceHistory: (id) => API.get(`/api/price-history/${id}`),
    refreshPrices: () => API.post('/api/refresh-prices'),
    getNotifications: () => API.get('/api/notifications'),
    markNotificationsRead: () => API.post('/api/notifications/read'),
    healthCheck: () => API.get('/api/health'),
};
