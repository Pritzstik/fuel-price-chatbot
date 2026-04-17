# Fuel Price Chatbot (LLM-Powered)

A full-stack chatbot app that:

1. Pulls nearby station prices from your Fuel Finder API.
2. Stores fuel prices in SQLite.
3. Uses an LLM to answer questions like:
   - "What is the cheapest fuel price near me?"
   - "What's the cheapest diesel near me?"

## Tech stack

- **Backend**: Python standard library (`http.server`, `urllib`, `sqlite3`)
- **Database**: SQLite
- **Frontend**: Vanilla HTML/CSS/JS
- **LLM**: OpenAI-compatible Chat Completions API

## Setup

```bash
cp .env.example .env
```

Populate `.env` with:
- Fuel Finder credentials (`FUEL_FINDER_PUBLIC_KEY`, `FUEL_FINDER_SECRET_KEY`)
- Fuel Finder base URL (`FUEL_FINDER_BASE_URL`)
- Optional LLM settings (`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`)

## Run

```bash
set -a && source .env && set +a
python3 app.py
```

Open: `http://localhost:8080`

## Endpoints

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
  - response includes:
    - `reply` (LLM-generated if configured)
    - `results` (station list sorted cheapest first)
    - `llm_used` (`true`/`false`)

- `GET /api/stations?lat=...&lon=...&radius_km=...`
  - fetches + stores latest station prices

- `GET /api/health`
  - basic liveness check

## How LLM integration works

- The app always queries SQLite for cheapest stations first.
- If `OPENAI_API_KEY` is set, top results are sent to the LLM to produce a natural-language answer.
- If LLM is unavailable, the app gracefully falls back to a deterministic summary.

## Fuel Finder mapping notes

`fuel_service.py` includes normalization logic for expected station/price payloads. If your API response shape differs, update `_normalize()` and the path/query used in `fetch_prices()`.

## Security notes

- Keep secrets only in environment variables.
- Do not commit `.env`.
