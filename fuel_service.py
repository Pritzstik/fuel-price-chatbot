import base64
import json
from datetime import datetime, timezone
from urllib import error, parse, request

from db import upsert_station_prices


class FuelFinderClient:
    def __init__(self, base_url: str, public_key: str, secret_key: str):
        self.base_url = base_url.rstrip("/")
        self.public_key = public_key
        self.secret_key = secret_key

    def _headers(self) -> dict[str, str]:
        if not self.public_key or not self.secret_key:
            raise RuntimeError("Fuel Finder credentials are missing.")

        token = base64.b64encode(f"{self.public_key}:{self.secret_key}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
        }

    def fetch_prices(self, lat: float, lon: float, radius_km: float) -> list[dict]:
        # Replace path/params to match the exact Fuel Finder API docs.
        url = f"{self.base_url}/prices?{parse.urlencode({'lat': lat, 'lon': lon, 'radius_km': radius_km})}"
        req = request.Request(url, headers=self._headers(), method="GET")

        try:
            with request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise RuntimeError(f"Fuel Finder API error: HTTP {exc.code}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Fuel Finder API unreachable: {exc.reason}") from exc

        return self._normalize(payload)

    def _normalize(self, payload: dict) -> list[dict]:
        """
        Expected API shape (adjust mapping if your provider differs):
        {
          "stations": [
            {
              "id": "abc123",
              "name": "Station 1",
              "location": {"lat": -33.8, "lon": 151.2},
              "prices": [
                {"fuel_type": "unleaded", "price": 1.75},
                {"fuel_type": "diesel", "price": 1.83}
              ]
            }
          ]
        }
        """

        stations = payload.get("stations", [])
        rows: list[dict] = []
        fetched_at = datetime.now(timezone.utc).isoformat()

        for station in stations:
            sid = str(station.get("id", ""))
            name = station.get("name", "Unknown Station")
            loc = station.get("location", {})
            lat = float(loc.get("lat", 0))
            lon = float(loc.get("lon", 0))

            for price in station.get("prices", []):
                fuel_type = str(price.get("fuel_type", "unknown"))
                value = float(price.get("price", 0))
                rows.append(
                    {
                        "station_id": sid,
                        "station_name": name,
                        "fuel_type": fuel_type,
                        "price": value,
                        "latitude": lat,
                        "longitude": lon,
                        "fetched_at": fetched_at,
                    }
                )

        return rows

    def fetch_and_store(self, lat: float, lon: float, radius_km: float) -> list[dict]:
        rows = self.fetch_prices(lat=lat, lon=lon, radius_km=radius_km)
        upsert_station_prices(rows)
        return rows
