import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "fuel_prices.db"))


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS station_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL,
                station_name TEXT NOT NULL,
                fuel_type TEXT NOT NULL,
                price REAL NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                fetched_at TEXT NOT NULL,
                UNIQUE(station_id, fuel_type, fetched_at)
            )
            """
        )


def upsert_station_prices(rows: list[dict]) -> None:
    if not rows:
        return

    with get_conn() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO station_prices
                (station_id, station_name, fuel_type, price, latitude, longitude, fetched_at)
            VALUES
                (:station_id, :station_name, :fuel_type, :price, :latitude, :longitude, :fetched_at)
            """,
            rows,
        )


def query_cheapest(lat: float, lon: float, radius_km: float, fuel_type: str | None = None) -> list[sqlite3.Row]:
    """Simple bounding-box filter by radius for local usage."""

    degree_delta = radius_km / 111.0

    sql = """
        SELECT station_name, station_id, fuel_type, price, latitude, longitude, fetched_at
        FROM station_prices
        WHERE latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
    """
    params: list[float | str] = [
        lat - degree_delta,
        lat + degree_delta,
        lon - degree_delta,
        lon + degree_delta,
    ]

    if fuel_type:
        sql += " AND LOWER(fuel_type) = LOWER(?)"
        params.append(fuel_type)

    sql += " ORDER BY price ASC LIMIT 10"

    with get_conn() as conn:
        return list(conn.execute(sql, params).fetchall())
