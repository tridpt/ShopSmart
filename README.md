# 🛒 ShopSmart AI Agent

AI-powered shopping assistant that helps you find the best deals, compare prices, and track product prices across the web.

![ShopSmart AI](https://img.shields.io/badge/AI-Shopping%20Agent-6C63FF?style=for-the-badge&logo=robot&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini%20AI-4285F4?style=for-the-badge&logo=google&logoColor=white)

## Features

- **AI Chat Interface** — Chat naturally to search products and compare prices
- **Web Search Tool** — Search across the internet for products and deals
- **Price Scraper** — Extract prices from product pages automatically
- **Price Tracking** — Track products and monitor price changes over time
- **Price Analysis** — AI-powered trend analysis and buying recommendations
- **Notifications** — Get alerts when prices drop to your target

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Brain | Google Gemini 2.0 Flash |
| Backend | Python + Flask |
| Database | SQLite |
| Frontend | HTML + CSS + JavaScript |
| Charts | Chart.js |
| Search | DuckDuckGo Search |

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/ShopSmart.git
cd ShopSmart
pip install -r requirements.txt
```

### 2. Set API Key

Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
# Windows PowerShell
$env:GEMINI_API_KEY='your_api_key_here'

# Windows CMD
set GEMINI_API_KEY=your_api_key_here

# Linux/Mac
export GEMINI_API_KEY='your_api_key_here'
```

### 3. Run

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## Architecture

```
ShopSmart/
├── app.py                  # Flask server & API endpoints
├── config.py               # Configuration
├── requirements.txt        # Python dependencies
├── agent/
│   ├── core.py             # AI Agent with ReAct loop
│   ├── prompts.py          # System prompts
│   └── tools/
│       ├── web_search.py   # DuckDuckGo product search
│       ├── price_scraper.py# Price extraction from URLs
│       ├── price_tracker.py# Database price tracking
│       ├── price_analyzer.py# Price trend analysis
│       └── notifier.py     # Notification system
├── database/
│   ├── db.py               # SQLite connection & schema
│   └── models.py           # Data models (CRUD)
└── frontend/
    ├── index.html           # Single-page application
    ├── css/                 # Dark theme UI styles
    └── js/                  # Chat, dashboard, notifications
```

## Agent Tools

| Tool | Description |
|------|-------------|
| `search_product` | Search products across the web |
| `scrape_price` | Extract price from a product URL |
| `track_price` | Add product to price watchlist |
| `analyze_price` | Analyze price trends & recommendations |
| `get_tracked_products` | View all tracked products |
| `send_notification` | Create price drop alerts |

## License

MIT License
