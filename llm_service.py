import json
import os
from urllib import error, request


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY", "")
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")
        self.model = model or os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL", "")
        self.timeout_seconds = timeout_seconds or float(os.environ.get("LLM_TIMEOUT_SECONDS", "10"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    def generate_fuel_reply(
        self,
        question: str,
        fuel_type: str | None,
        radius_km: float,
        results: list[dict],
        fallback_reply: str,
    ) -> str:
        if not self.enabled:
            return fallback_reply

        system_prompt = (
            "You are a concise fuel price assistant. Answer only from the station "
            "price data provided by the application. Do not invent prices, station "
            "names, locations, discounts, opening hours, or availability. If the "
            "data is not enough, say what is missing and keep the deterministic "
            "results as the source of truth."
        )
        user_prompt = {
            "question": question,
            "requested_fuel_type": fuel_type,
            "search_radius_km": radius_km,
            "results_sorted_by_price": results,
            "fallback_reply": fallback_reply,
            "instructions": (
                "Give a helpful natural-language answer in 1-3 short sentences. "
                "Mention the cheapest option first and refer to the table for more options."
            ),
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt)},
            ],
            "temperature": 0.2,
            "max_tokens": 180,
        }

        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
            return fallback_reply

        try:
            content = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            return fallback_reply

        return content or fallback_reply
