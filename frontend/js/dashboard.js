/**
 * ShopSmart AI — Dashboard Logic
 */
const Dashboard = {
    chart: null,
    _products: [],
    _sortBy: 'name',

    init() {
        const refreshBtn = document.getElementById('btn-refresh-prices');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshPrices());
        }
        const exportBtn = document.getElementById('btn-export-tracked');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportCsv());
        }
        const sortSel = document.getElementById('tracking-sort');
        if (sortSel) {
            sortSel.addEventListener('change', () => {
                this._sortBy = sortSel.value;
                this.updateTrackingList(this._products);
            });
        }
        const filterInput = document.getElementById('tracking-filter');
        if (filterInput) {
            filterInput.addEventListener('input', () => this.updateTrackingList(this._products));
        }
        this.refresh();
    },

    async exportCsv() {
        try {
            const res = await fetch(API.exportTrackedUrl(), { headers: API._headers() });
            if (!res.ok) {
                alert('Không thể xuất CSV.');
                return;
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'shopsmart-tracked.csv';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Export CSV failed:', e);
            alert('Lỗi khi xuất CSV.');
        }
    },

    async refreshPrices() {
        const btn = document.getElementById('btn-refresh-prices');
        const icon = btn ? btn.querySelector('i') : null;
        if (btn) btn.disabled = true;
        if (icon) icon.classList.add('fa-spin');
        try {
            const data = await API.refreshPrices();
            if (data && data.success) {
                const n = data.updated || 0;
                alert(n > 0
                    ? `Đã cập nhật giá cho ${n} sản phẩm.`
                    : 'Đã kiểm tra xong. Không có sản phẩm nào đổi giá.');
            } else {
                alert('Không thể làm mới giá: ' + ((data && data.error) || 'lỗi không xác định'));
            }
            this.refresh();
            if (typeof Notifications !== 'undefined') Notifications.refresh();
        } catch (e) {
            console.error('Refresh prices error:', e);
            alert('Lỗi kết nối khi làm mới giá.');
        } finally {
            if (btn) btn.disabled = false;
            if (icon) icon.classList.remove('fa-spin');
        }
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
            this._products = products;
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
        } catch (e) {
            console.warn('Dashboard.refresh failed:', e);
        }
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

            // Identify the all-time low / high points so we can highlight them.
            const minPrice = Math.min(...prices);
            const maxPrice = Math.max(...prices);
            const minIdx = prices.indexOf(minPrice);
            const maxIdx = prices.indexOf(maxPrice);

            const pointColors = prices.map((_, i) => {
                if (i === minIdx) return '#2ECC71';   // lowest ever → green
                if (i === maxIdx) return '#FF6B6B';    // highest ever → red
                return '#6C63FF';
            });
            const pointRadii = prices.map((_, i) =>
                (i === minIdx || i === maxIdx) ? 7 : 3);

            if (this.chart) this.chart.destroy();

            const ctx = document.getElementById('price-chart').getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(108, 99, 255, 0.3)');
            gradient.addColorStop(1, 'rgba(108, 99, 255, 0)');

            // Show a small legend line summarising the min/max.
            const statsEl = document.getElementById('chart-stats');
            if (statsEl) {
                statsEl.innerHTML =
                    `<span class="chart-stat low"><i class="fas fa-arrow-down"></i> Thấp nhất: ${minPrice.toLocaleString('vi-VN')}đ</span>` +
                    `<span class="chart-stat high"><i class="fas fa-arrow-up"></i> Cao nhất: ${maxPrice.toLocaleString('vi-VN')}đ</span>`;
            }

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
                        pointBackgroundColor: pointColors,
                        pointBorderColor: pointColors,
                        pointRadius: pointRadii,
                        pointHoverRadius: 8,
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

        // Apply free-text filter (matches name or source).
        const filterEl = document.getElementById('tracking-filter');
        const q = (filterEl ? filterEl.value : '').trim().toLowerCase();
        let rows = products.slice();
        if (q) {
            rows = rows.filter(p =>
                (p.name || '').toLowerCase().includes(q) ||
                (p.source || '').toLowerCase().includes(q));
        }

        // Apply sort.
        const sortBy = this._sortBy || 'name';
        const num = (v) => (v == null ? null : Number(v));
        const dropPct = (p) => {
            const cur = num(p.current_price), tgt = num(p.target_price);
            if (cur == null || tgt == null || cur <= 0) return null;
            return ((cur - tgt) / cur) * 100; // how far above target, as %
        };
        rows.sort((a, b) => {
            switch (sortBy) {
                case 'price_asc': return (num(a.current_price) ?? Infinity) - (num(b.current_price) ?? Infinity);
                case 'price_desc': return (num(b.current_price) ?? -Infinity) - (num(a.current_price) ?? -Infinity);
                case 'drop': return (dropPct(b) ?? -Infinity) - (dropPct(a) ?? -Infinity);
                case 'name':
                default: return (a.name || '').localeCompare(b.name || '', 'vi');
            }
        });

        if (rows.length === 0) {
            list.innerHTML = `<div class="empty-state"><i class="fas fa-filter"></i><h3>Không có sản phẩm khớp bộ lọc</h3></div>`;
            return;
        }

        list.innerHTML = rows.map(p => {
            const price = p.current_price ? `${Number(p.current_price).toLocaleString('vi-VN')}đ` : 'N/A';
            const targetVal = p.target_price ? Number(p.target_price) : '';
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
                        <div class="track-target-edit">
                            <input type="number" min="0" step="1000" placeholder="Giá mục tiêu"
                                   value="${targetVal}" id="target-input-${p.id}" class="target-input">
                            <button class="btn-set-target" onclick="Dashboard.setTarget(${p.id})" title="Lưu giá mục tiêu">
                                <i class="fas fa-check"></i>
                            </button>
                        </div>
                    </div>
                    <div class="track-actions">
                        <button class="btn-icon" title="Xóa" onclick="Dashboard.deleteProduct(${p.id})">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </div>`;
        }).join('');
    },

    async setTarget(id) {
        const input = document.getElementById(`target-input-${id}`);
        if (!input) return;
        const raw = input.value.trim();
        const price = raw === '' ? null : Number(raw);
        if (price !== null && (!isFinite(price) || price <= 0)) {
            alert('Giá mục tiêu phải là số dương.');
            return;
        }
        try {
            const data = await API.updateTarget(id, price);
            if (data && data.error) {
                alert('Không thể cập nhật: ' + data.error);
                return;
            }
            this.refresh();
        } catch (e) {
            console.error('Dashboard.setTarget failed:', e);
            alert('Lỗi khi lưu giá mục tiêu.');
        }
    },

    async deleteProduct(id) {
        if (!confirm('Xóa sản phẩm khỏi danh sách theo dõi?')) return;
        try {
            await API.deleteTracked(id);
            this.refresh();
        } catch (e) {
            console.error('Dashboard.deleteProduct failed:', e);
        }
    }
};
