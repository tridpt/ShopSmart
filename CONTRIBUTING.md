# Contributing to ShopSmart

Thanks for your interest in improving ShopSmart! This guide covers local setup
and the basics for contributing.

## Setup

```bash
git clone https://github.com/tridpt/ShopSmart.git
cd ShopSmart
pip install -r requirements.txt
cp .env.example .env   # then fill in GEMINI_API_KEY
```

## Running

```bash
python app.py        # dev server at http://127.0.0.1:5000
python serve.py      # production server (waitress)
```

## Tests

Please run the test suite before opening a pull request:

```bash
pytest
```

Tests run against an isolated temporary SQLite database, so they never touch
your real `shopsmart.db`. `BCRYPT_ROUNDS=4` is set automatically in tests to
keep password hashing fast.

If you add a feature or fix a bug, add a test for it where practical.

## Pull requests

- Keep changes focused; one logical change per PR.
- Describe what changed and how you verified it.
- Make sure `pytest` passes and no secrets (`.env`, `.jwt_secret`) are committed.

## Code style

- Match the existing style of the file you're editing.
- Prefer clear names and small functions over cleverness.
- Backend is plain Flask + SQLite; frontend is vanilla HTML/CSS/JS (no build step).
