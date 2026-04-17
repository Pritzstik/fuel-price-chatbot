# Fuel Price Chatbot

A lightweight full-stack chatbot app that:

1. Pulls nearby station prices from your Fuel Finder API.
2. Stores fuel prices in SQLite.
3. Answers questions like:
   - "What is the cheapest fuel price near me?"
   - "What's the cheapest diesel near me?"

## Tech stack

- **Backend**: Python standard library (`http.server`, `urllib`, `sqlite3`)
- **Database**: SQLite
- **Frontend**: Vanilla HTML/CSS/JS

## Setup

```bash
cp .env.example .env
```

Populate `.env` with your Fuel Finder credentials and base URL.

### Run

```bash
set -a && source .env && set +a
python3 app.py
```

Open: `http://localhost:8080`

## API endpoints

- `POST /api/chat`
  - body:
    ```json
    {
      "question": "What is the cheapest diesel near me?",
      "lat": 37.7749,
      "lon": -122.4194,
      "radius_km": 10
    }
    ```
- `GET /api/stations?lat=...&lon=...&radius_km=...`
  - fetches + stores latest station prices

## Fuel Finder mapping notes

`fuel_service.py` contains the API normalization logic. If your Fuel Finder response shape differs, update `_normalize()` and URL path/query in `fetch_prices()`.

## Security notes

- Keep secrets only in environment variables.
- Do not commit `.env`.

