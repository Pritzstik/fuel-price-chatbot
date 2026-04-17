import re

from db import query_cheapest
from llm_service import LLMClient

SUPPORTED_FUEL_TYPES = ["unleaded", "premium", "diesel", "e10", "lpg"]


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
        }

    if fuel_type:
        lead = f"Cheapest {fuel_type} near you"
    else:
        lead = "Cheapest fuel prices near you"

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

    best = formatted[0]
    reply = (
        f"{lead}: {best['station']} has {best['fuel_type']} at {best['price']:.3f}. "
        "I've included more nearby options sorted by lowest price."
    )
    reply = LLMClient().generate_fuel_reply(
        question=question,
        fuel_type=fuel_type,
        radius_km=radius_km,
        results=formatted,
        fallback_reply=reply,
    )

    return {"reply": reply, "results": formatted}
