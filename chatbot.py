import re

from db import query_cheapest
from llm_service import LLMClient

SUPPORTED_FUEL_TYPES = ["unleaded", "premium", "diesel", "e10", "lpg"]
llm_client = LLMClient()


def extract_fuel_type(question: str) -> str | None:
    lower_q = question.lower()
    for fuel_type in SUPPORTED_FUEL_TYPES:
        if re.search(rf"\b{re.escape(fuel_type)}\b", lower_q):
            return fuel_type
    return None


def answer_question(question: str, lat: float, lon: float, radius_km: float) -> dict:
    fuel_type = extract_fuel_type(question)
    rows = query_cheapest(lat=lat, lon=lon, radius_km=radius_km, fuel_type=fuel_type)

    if not rows:
        return {
            "reply": "I couldn't find fuel prices nearby. Try increasing the search radius.",
            "results": [],
            "llm_used": False,
        }

    formatted = [
        {
            "station": row["station_name"],
            "station_id": row["station_id"],
            "fuel_type": row["fuel_type"],
            "price": row["price"],
            "location": {"lat": row["latitude"], "lon": row["longitude"]},
            "fetched_at": row["fetched_at"],
        }
        for row in rows
    ]

    llm_used = llm_client.is_configured()
    if llm_used:
        reply = llm_client.generate_price_answer(question=question, candidates=formatted[:5])
    else:
        best = formatted[0]
        reply = (
            f"Cheapest near you: {best['station']} has {best['fuel_type']} at {best['price']:.3f}. "
            "Add OPENAI_API_KEY to enable LLM-generated responses."
        )

    return {"reply": reply, "results": formatted, "llm_used": llm_used}
