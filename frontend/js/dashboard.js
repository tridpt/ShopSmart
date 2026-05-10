/**
 * ShopSmart AI — Dashboard Logic
 */
const Dashboard = {
    chart: null,

    init() {
        this.refresh();
    },

    async refresh() {
        try {
            // Refresh stats
            const [tracked, notifications, chatHistory] = await Promise.all([
                API.getTracked(),
                API.getNotifications(),
                API.getChatHistory(),
            ]);

            const products = tracked.products || [];
            document.getElementById('stat-total').textContent = products.length;
            document.getElementById('stat-alerts').textContent = notifications.unread_count || 0;
            document.getElementById('stat-chats').textContent = (chatHistory.history || []).length;
            document.getElementById('stat-deals').textContent = (notifications.notifications || [])
                .filter(n => n.type === 'deal').length;

            // Update tracking badge
            const badge = document.getElementById('tracking-badge');
            if (products.length > 0) {
                badge.textContent = products.length;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }

            // Update chart selector
            this.updateChartSelector(products);

            // Update tracking list
            this.updateTrackingList(products);
        } catch (e) { /* ignore */ }
    },

    updateChartSelector(products) {
        const select = document.getElementById('chart-product-select');
        const placeholder = document.getElementById('chart-placeholder');
        const container = document.getElementById('chart-container');

        if (products.length === 0) {
            placeholder.style.display = 'flex';
            container.style.display = 'none';
            return;
        }

        placeholder.style.display = 'none';
        container.style.display = 'block';

        const currentVal = select.value;
        select.innerHTML = '<option value="">-- Chọn sản phẩm --</option>';
        products.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            select.appendChild(opt);
        });

        if (currentVal) select.value = currentVal;

        select.onchange = () => {
            if (select.value) this.loadChart(select.value);
        };

        // Auto-select first product
        if (!currentVal && products.length > 0) {
            select.value = products[0].id;
            this.loadChart(products[0].id);
        }
    },

    async loadChart(productId) {
        try {
            const data = await API.getPriceHistory(productId);
            const history = data.history || [];

            if (history.length === 0) return;

            const labels = history.map(h => {
                const d = new Date(h.recorded_at);
                return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
            });
            const prices = history.map(h => h.price);

            if (this.chart) this.chart.destroy();

            const ctx = document.getElementById('price-chart').getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(108, 99, 255, 0.3)');
            gradient.addColorStop(1, 'rgba(108, 99, 255, 0)');

            this.chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Giá (VND)',
                        data: prices,
                        borderColor: '#6C63FF',
                        backgroundColor: gradient,
                        borderWidth: 2,
                        pointBackgroundColor: '#6C63FF',
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        fill: true,
                        tension: 0.4,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#1a1a2e',
                            borderColor: '#6C63FF',
                            borderWidth: 1,
                            titleColor: '#e8e8f0',
                            bodyColor: '#9a9ab0',
                            callbacks: {
                                label: (ctx) => `${ctx.parsed.y.toLocaleString('vi-VN')}đ`
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#6a6a80', font: { size: 11 } }
                        },
                        y: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: {
                                color: '#6a6a80',
                                font: { size: 11 },
                                callback: (v) => (v / 1000000).toFixed(1) + 'tr'
                            }
                        }
                    }
                }
            });
        } catch (e) { console.error('Chart error:', e); }
    },

    updateTrackingList(products) {
        const list = document.getElementById('tracking-list');
        if (products.length === 0) {
            list.innerHTML = `<div class="empty-state"><i class="fas fa-box-open"></i><h3>Chưa có sản phẩm nào</h3><p>Chat với AI để tìm và theo dõi giá sản phẩm!</p><button class="btn-primary" onclick="switchView('chat')"><i class="fas fa-comments"></i> Bắt đầu chat</button></div>`;
            return;
        }

        list.innerHTML = products.map(p => {
            const price = p.current_price ? `${Number(p.current_price).toLocaleString('vi-VN')}đ` : 'N/A';
            const target = p.target_price ? `Mục tiêu: ${Number(p.target_price).toLocaleString('vi-VN')}đ` : '';
            const source = p.source || 'Web';
            return `
                <div class="track-card animate-fade-in">
                    <div class="track-icon"><i class="fas fa-tag"></i></div>
                    <div class="track-info">
                        <div class="track-name">${p.name}</div>
                        <div class="track-source">${source}${p.url ? ` · <a href="${p.url}" target="_blank" style="color:var(--accent-cyan)">Xem →</a>` : ''}</div>
                    </div>
                    <div class="track-price">
                        <span class="track-current">${price}</span>
                        <span class="track-target">${target}</span>
                    </div>
                    <div class="track-actions">
                        <button class="btn-icon" title="Xóa" onclick="Dashboard.deleteProduct(${p.id})">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </div>`;
        }).join('');
    },

    async deleteProduct(id) {
        if (!confirm('Xóa sản phẩm khỏi danh sách theo dõi?')) return;
        try {
            await API.deleteTracked(id);
            this.refresh();
        } catch (e) { /* ignore */ }
    }
};
