/**
 * ShopSmart AI — API Client
 */
const API = {
    BASE: '',

    async post(endpoint, data) {
        const res = await fetch(`${this.BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return res.json();
    },

    async get(endpoint) {
        const res = await fetch(`${this.BASE}${endpoint}`);
        return res.json();
    },

    async del(endpoint) {
        const res = await fetch(`${this.BASE}${endpoint}`, { method: 'DELETE' });
        return res.json();
    },

    async put(endpoint, data) {
        const res = await fetch(`${this.BASE}${endpoint}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return res.json();
    },

    // Convenience methods
    sendMessage: (message) => API.post('/api/chat', { message }),
    getChatHistory: () => API.get('/api/chat/history'),
    clearChat: () => API.post('/api/chat/clear'),
    getTracked: () => API.get('/api/tracked'),
    deleteTracked: (id) => API.del(`/api/tracked/${id}`),
    updateTarget: (id, price) => API.put(`/api/tracked/${id}/target`, { target_price: price }),
    getPriceHistory: (id) => API.get(`/api/price-history/${id}`),
    getNotifications: () => API.get('/api/notifications'),
    markNotificationsRead: () => API.post('/api/notifications/read'),
    healthCheck: () => API.get('/api/health'),
};
