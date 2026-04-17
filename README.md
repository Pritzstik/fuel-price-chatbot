# Fuel Price Chatbot

A lightweight full-stack chatbot app that:

1. Pulls nearby station prices from your Fuel Finder API.
2. Stores fuel prices in SQLite.
3. Optionally uses an OpenAI-compatible LLM to generate natural-language answers grounded in the stored price data.
4. Answers questions like:
   - "What is the cheapest fuel price near me?"
   - "What's the cheapest diesel near me?"

## Tech stack

- **Backend**: Python standard library (`http.server`, `urllib`, `sqlite3`)
- **Database**: SQLite
- **Frontend**: Vanilla HTML/CSS/JS

## Setup

Create or update the local `.env` file in the project root. The app loads this file automatically on startup.

Required Fuel Finder settings:

```bash
FUEL_FINDER_BASE_URL=https://api.fuelfinder.service.gov.uk/v1
FUEL_FINDER_PRICES_PATH=/prices
FUEL_FINDER_TOKEN_URL=https://your-token-endpoint
FUEL_FINDER_PUBLIC_KEY=your_client_id
FUEL_FINDER_SECRET_KEY=your_client_secret
```

Optional Fuel Finder settings:

```bash
FUEL_FINDER_AUTH_TYPE=oauth
FUEL_FINDER_SCOPE=fuelfinder.read
FUEL_FINDER_ACCESS_TOKEN=your_existing_access_token
FUEL_FINDER_TIMEOUT_SECONDS=15
```

The Fuel Finder public API uses OAuth 2 client credentials. If your
`FUEL_FINDER_BASE_URL` already points at the full `/v1/prices` endpoint, set
`FUEL_FINDER_PRICES_PATH=` to an empty value.
If you already have a valid bearer token, set `FUEL_FINDER_ACCESS_TOKEN` and the
app will use it directly instead of requesting a new token.

Optional LLM settings:

```bash
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=your_model_name
# Optional for OpenAI-compatible providers:
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=10
```

If `OPENAI_API_KEY` or `OPENAI_MODEL` is missing, the chatbot falls back to the built-in deterministic response.

### Run

```powershell
python app.py
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

`fuel_service.py` contains the API normalization logic. It supports common payloads where station rows are under `stations`, `results`, `data`, `items`, or at the top level. If your provider uses different field names, update `_normalize()`.
