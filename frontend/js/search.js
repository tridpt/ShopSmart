/**
 * ShopSmart AI — Direct Search (No AI needed)
 */
const Search = {
    inputEl: null,
    btnEl: null,
    resultsEl: null,
    statusEl: null,
    isSearching: false,

    init() {
        this.inputEl = document.getElementById('search-input');
        this.btnEl = document.getElementById('btn-search');
        this.resultsEl = document.getElementById('search-results');
        this.statusEl = document.getElementById('search-status');

        this.btnEl.addEventListener('click', () => this.doSearch());
        this.inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.doSearch();
        });

        // Tag buttons
        document.querySelectorAll('.search-tag').forEach(tag => {
            tag.addEventListener('click', () => {
                this.inputEl.value = tag.dataset.q;
                this.doSearch();
            });
        });
    },

    async doSearch() {
        const query = this.inputEl.value.trim();
        if (!query || this.isSearching) return;

        this.isSearching = true;
        this.btnEl.disabled = true;
        this.btnEl.textContent = 'Searching...';

        // Show loading
        this.statusEl.style.display = 'flex';
        this.statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Searching on Shopee, Tiki, CellphoneS, FPT Shop, Lazada...';

        // Show skeleton cards
        this.resultsEl.innerHTML = Array(6).fill('<div class="product-skeleton"></div>').join('');

        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();

            if (data.error) {
                this.statusEl.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${data.error}`;
                this.resultsEl.innerHTML = '';
            } else {
                this.renderResults(data, query);
            }
        } catch (err) {
            this.statusEl.innerHTML = '<i class="fas fa-exclamation-circle"></i> Connection error';
            this.resultsEl.innerHTML = '';
        }

        this.isSearching = false;
        this.btnEl.disabled = false;
        this.btnEl.textContent = 'Search';
    },

    renderResults(data, query) {
        const results = data.results || [];
        const summary = data.price_summary || {};

        // Status
        if (results.length === 0) {
            this.statusEl.innerHTML = `<i class="fas fa-info-circle"></i> No results for "${query}". Try different keywords.`;
            this.resultsEl.innerHTML = '';
            return;
        }

        let statusHtml = `<i class="fas fa-check-circle"></i> Found <strong>${results.length}</strong> results for "${query}"`;
        if (summary.lowest_formatted) {
            statusHtml += ` &mdash; Price: <strong>${summary.lowest_formatted}</strong> ~ <strong>${summary.highest_formatted}</strong>`;
        }
        if (summary.sources_found) {
            statusHtml += ` &mdash; Sources: ${summary.sources_found.join(', ')}`;
        }
        this.statusEl.innerHTML = statusHtml;

        // Render cards
        this.resultsEl.innerHTML = results.map(r => {
            const source = r.source || 'Web';
            const badgeClass = this._sourceBadgeClass(source);
            const price = r.price_formatted
                ? `<span class="product-price">${r.price_formatted}</span>`
                : `<span class="product-price no-price">View price on site</span>`;
            const snippet = r.snippet ? `<div class="product-snippet">${r.snippet}</div>` : '';
            const link = r.url ? `<a href="${r.url}" target="_blank" class="btn-visit"><i class="fas fa-external-link-alt"></i> View</a>` : '';

            return `
                <div class="product-card">
                    <div class="product-header">
                        <span class="product-source-badge ${badgeClass}">${source}</span>
                        <div class="product-name">${r.product_name || 'Unknown product'}</div>
                    </div>
                    ${snippet}
                    <div class="product-footer">
                        ${price}
                        <div class="product-actions">${link}</div>
                    </div>
                </div>`;
        }).join('');
    },

    _sourceBadgeClass(source) {
        const map = {
            'Shopee': 'shopee', 'Tiki': 'tiki', 'Lazada': 'lazada',
            'CellphoneS': 'cellphones', 'FPT Shop': 'fptshop',
            'The Gioi Di Dong': 'tgdd', 'Dien May Xanh': 'dmx',
        };
        return map[source] || 'web';
    }
};
