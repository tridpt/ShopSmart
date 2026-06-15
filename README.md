# 🛒 ShopSmart AI Agent

AI-powered shopping assistant that helps you find the best deals, compare prices, and track product prices across the web.

![ShopSmart AI](https://img.shields.io/badge/AI-Shopping%20Agent-6C63FF?style=for-the-badge&logo=robot&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini%20AI-4285F4?style=for-the-badge&logo=google&logoColor=white)

## Features

- **Multi-user accounts** — Register/login with JWT auth; every user's tracked products, chats and notifications are private to them
- **AI Chat Interface** — Chat naturally to search products and compare prices
- **Web Search Tool** — Search across the internet for products and deals
- **Price Scraper** — Extract prices from product pages automatically (site-specific selectors + sane price-range validation)
- **Price Tracking** — Track products and monitor price changes over time
- **Auto price monitor** — Background job re-scrapes tracked products on a schedule and records history
- **Price Analysis** — AI-powered trend analysis and buying recommendations
- **Real notifications** — In-app alerts plus optional Telegram / email push when a price drops or hits your target

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Brain | Google Gemini 2.5 Flash (`google-genai` SDK) |
| Backend | Python + Flask |
| Auth | JWT (PyJWT) + bcrypt |
| Database | SQLite |
| Frontend | HTML + CSS + JavaScript |
| Charts | Chart.js |
| Search | DuckDuckGo Search |
| Push channels | Telegram Bot API, SMTP email |
| Tests | pytest |

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

Open **http://127.0.0.1:5000** in your browser, then register an account to get started.

## Configuration

Copy `.env.example` to `.env` and fill in what you need. Only `GEMINI_API_KEY` is required.

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Gemini API key (required for AI chat) |
| `JWT_SECRET` | Secret for signing auth tokens. **Set this in production.** A local one is auto-generated for dev. |
| `FLASK_DEBUG` | `true` to enable debug mode (default off) |
| `PRICE_MONITOR_ENABLED` | `false` to disable the background price monitor |
| `PRICE_MONITOR_INTERVAL` | Seconds between scan cycles (default 6h) |
| `TELEGRAM_BOT_TOKEN` | Enable Telegram price alerts |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Enable email price alerts |

> Note: the background price monitor runs inside the Flask process. If you deploy
> behind a multi-worker WSGI server, run the monitor as a separate process to
> avoid duplicate scans.

## Testing

```bash
pytest
```

Tests run against an isolated temporary SQLite database — they never touch `shopsmart.db`.

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
