import base64
import json
import os
from datetime import datetime, timezone
from urllib import error, parse, request

from db import upsert_station_prices


class FuelFinderClient:
    def __init__(
        self,
        base_url: str,
        public_key: str,
        secret_key: str,
        prices_path: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.client_id = public_key
        self.client_secret = secret_key
        self.auth_type = os.environ.get("FUEL_FINDER_AUTH_TYPE", "oauth").strip().lower()
        self.token_url = os.environ.get("FUEL_FINDER_TOKEN_URL", "").strip()
        self.scope = os.environ.get("FUEL_FINDER_SCOPE", "fuelfinder.read").strip()
        self.prices_path = self._resolve_prices_path(prices_path)
        self.timeout_seconds = timeout_seconds or float(os.environ.get("FUEL_FINDER_TIMEOUT_SECONDS", "15"))
        self._access_token: str | None = os.environ.get("FUEL_FINDER_ACCESS_TOKEN", "").strip() or None

    def _resolve_prices_path(self, prices_path: str | None) -> str:
        if prices_path is not None:
            return prices_path
        if "FUEL_FINDER_PRICES_PATH" in os.environ:
            return os.environ["FUEL_FINDER_PRICES_PATH"]
        if self.base_url.rstrip("/").endswith("/prices"):
            return ""
        return "/prices"

    def _headers(self) -> dict[str, str]:
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Fuel Finder credentials are missing.")

        if self.auth_type == "basic":
            token = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            return {
                "Authorization": f"Basic {token}",
                "Accept": "application/json",
            }

        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Accept": "application/json",
        }

    def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        if not self.token_url:
            raise RuntimeError("Fuel Finder OAuth token URL is missing. Set FUEL_FINDER_TOKEN_URL in .env.")

        form = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scope:
            form["scope"] = self.scope

        req = request.Request(
            self.token_url,
            data=parse.urlencode(form).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise RuntimeError(f"Fuel Finder OAuth token error: HTTP {exc.code}") from exc
        except error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise RuntimeError(f"Fuel Finder OAuth token endpoint unreachable: {reason}.") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Fuel Finder OAuth token endpoint returned invalid JSON.") from exc

        token = self._extract_access_token(payload)
        if not token:
            fields = self._describe_response_fields(payload)
            raise RuntimeError(
                "Fuel Finder OAuth token response did not include access_token. "
                f"Returned fields: {fields}."
            )

        self._access_token = str(token)
        return self._access_token

    def _extract_access_token(self, payload: dict) -> str | None:
        for source in (payload, payload.get("data")):
            if not isinstance(source, dict):
                continue

            token = self._first_value(
                source,
                ("access_token", "accessToken", "token", "bearer_token", "bearerToken"),
            )
            if token:
                return str(token)

        return None

    def _describe_response_fields(self, payload: dict) -> str:
        fields = ", ".join(sorted(payload.keys())) or "no fields"
        data = payload.get("data")
        if isinstance(data, dict):
            data_fields = ", ".join(sorted(data.keys())) or "no fields"
            fields = f"{fields}; data fields: {data_fields}"
        return fields

    def _build_url(self, lat: float, lon: float, radius_km: float) -> str:
        if "fuelfinder.example.com" in self.base_url:
            raise RuntimeError(
                "Fuel Finder base URL is still set to the placeholder host. "
                "Update FUEL_FINDER_BASE_URL in .env to your real provider URL."
            )

        params = parse.urlencode({"lat": lat, "lon": lon, "radius_km": radius_km})
        path = self.prices_path.strip()

        if path:
            path = "/" + path.strip("/")
            endpoint = f"{self.base_url}{path}"
        else:
            endpoint = self.base_url

        separator = "&" if "?" in endpoint else "?"
        return f"{endpoint}{separator}{params}"

    def _safe_endpoint(self, url: str) -> str:
        parsed = parse.urlparse(url)
        return parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

    def _first_value(self, source: dict, keys: tuple[str, ...], default=None):
        for key in keys:
            if key in source and source[key] is not None:
                return source[key]
        return default

    def fetch_prices(self, lat: float, lon: float, radius_km: float) -> list[dict]:
        url = self._build_url(lat=lat, lon=lon, radius_km=radius_km)
        req = request.Request(url, headers=self._headers(), method="GET")

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            endpoint = self._safe_endpoint(url)
            raise RuntimeError(f"Fuel Finder API error: HTTP {exc.code} for {endpoint}") from exc
        except error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise RuntimeError(
                f"Fuel Finder API unreachable: {reason}. "
                "Check FUEL_FINDER_BASE_URL and FUEL_FINDER_PRICES_PATH in .env."
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Fuel Finder API returned invalid JSON.") from exc

        return self._normalize(payload)

    def _station_list(self, payload: dict | list) -> list[dict]:
        if isinstance(payload, list):
            return payload

        for key in ("stations", "results", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

        nested = payload.get("data")
        if isinstance(nested, dict):
            return self._station_list(nested)

        return []

    def _location(self, station: dict) -> tuple[float, float]:
        loc = station.get("location") or station.get("coordinates") or {}
        lat = self._first_value(loc, ("lat", "latitude"), self._first_value(station, ("lat", "latitude"), 0))
        lon = self._first_value(
            loc,
            ("lon", "lng", "longitude"),
            self._first_value(station, ("lon", "lng", "longitude"), 0),
        )
        return float(lat), float(lon)

    def _prices(self, station: dict) -> list[dict]:
        prices = self._first_value(station, ("prices", "fuel_prices", "fuels"))

        if isinstance(prices, dict):
            return [{"fuel_type": fuel_type, "price": price} for fuel_type, price in prices.items()]

        if isinstance(prices, list):
            return [price for price in prices if isinstance(price, dict)]

        fuel_type = self._first_value(station, ("fuel_type", "fuelType"))
        price = self._first_value(station, ("price",))
        if fuel_type and price is not None:
            return [{"fuel_type": fuel_type, "price": price}]

        return []

    def _normalize(self, payload: dict) -> list[dict]:
        """
        Supports common API shapes where stations live under stations, results,
        data, items, or at the top level. Prices may be a list, a dict keyed by
        fuel type, or a single station-level fuel_type/price pair.
        """

        stations = self._station_list(payload)
        rows: list[dict] = []
        fetched_at = datetime.now(timezone.utc).isoformat()

        for station in stations:
            sid = str(self._first_value(station, ("id", "station_id", "site_id"), ""))
            name = self._first_value(station, ("name", "station_name", "brand"), "Unknown Station")
            lat, lon = self._location(station)

            for price in self._prices(station):
                fuel_type = str(self._first_value(price, ("fuel_type", "fuelType", "type"), "unknown"))
                value = self._first_value(price, ("price", "value", "amount"))
                if value is None:
                    continue

                rows.append(
                    {
                        "station_id": sid,
                        "station_name": name,
                        "fuel_type": fuel_type,
                        "price": float(value),
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
