import json
import os
from urllib import error, request


class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate_price_answer(self, question: str, candidates: list[dict]) -> str:
        if not candidates:
            return "I couldn't find fuel prices nearby. Try increasing the search radius."

        system_prompt = (
            "You are a fuel price assistant. Answer with practical, concise guidance based only on the provided station data. "
            "If the user asked for cheapest, highlight the cheapest first and include 2-4 alternatives. "
            "Mention fuel types and prices exactly from the data."
        )

        user_prompt = (
            f"User question: {question}\n"
            f"Station data (sorted by cheapest first):\n{json.dumps(candidates, ensure_ascii=False)}\n"
            "Return plain text only."
        )

        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        req = request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            data=json.dumps(payload).encode("utf-8"),
        )

        try:
            with request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"].strip()
        except (error.URLError, error.HTTPError, KeyError, IndexError, json.JSONDecodeError):
            best = candidates[0]
            return (
                f"Cheapest option: {best['station']} ({best['fuel_type']}) at {best['price']:.3f}. "
                "LLM response is temporarily unavailable, so I returned a deterministic summary."
            )
