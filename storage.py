"""Хранилище цен в SQLite: история наблюдений + отправленные уведомления.

Служит двум целям:
  1. Копит историю цен, чтобы считать "обычную" (медианную) цену маршрута.
  2. Хранит журнал уведомлений для антиспама (дедупликация).
"""
from __future__ import annotations

import os
import sqlite3
import statistics
from datetime import datetime, timedelta, timezone

import config


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS observations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                route       TEXT NOT NULL,
                trip_type   TEXT NOT NULL,
                price       REAL NOT NULL,
                depart_date TEXT,
                return_date TEXT,
                link        TEXT,
                found_at    TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_obs_route
                ON observations(route, trip_type, found_at);

            CREATE TABLE IF NOT EXISTS alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                route        TEXT NOT NULL,
                trip_type    TEXT NOT NULL,
                price_bucket INTEGER NOT NULL,
                price        REAL NOT NULL,
                sent_at      TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_key
                ON alerts(route, trip_type, price_bucket, sent_at);
            """
        )


def record_observation(route: str, trip_type: str, price: float,
                       depart_date: str | None, return_date: str | None,
                       link: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO observations "
            "(route, trip_type, price, depart_date, return_date, link, found_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (route, trip_type, price, depart_date, return_date, link,
             _now().isoformat()),
        )


def baseline_median(route: str, trip_type: str) -> float | None:
    """Медиана цен маршрута за окно BASELINE_WINDOW_DAYS.

    Возвращает None, если наблюдений меньше MIN_OBSERVATIONS.
    """
    since = (_now() - timedelta(days=config.BASELINE_WINDOW_DAYS)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT price FROM observations "
            "WHERE route = ? AND trip_type = ? AND found_at >= ?",
            (route, trip_type, since),
        ).fetchall()
    prices = [r["price"] for r in rows]
    if len(prices) < config.MIN_OBSERVATIONS:
        return None
    return statistics.median(prices)


def _price_bucket(price: float) -> int:
    return int(price // config.PRICE_BUCKET_SIZE)


def recently_alerted(route: str, trip_type: str, price: float) -> bool:
    """Было ли похожее уведомление (тот же маршрут/тип/ценовой бакет) недавно."""
    since = (_now() - timedelta(hours=config.ALERT_COOLDOWN_HOURS)).isoformat()
    bucket = _price_bucket(price)
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM alerts "
            "WHERE route = ? AND trip_type = ? AND price_bucket = ? "
            "AND sent_at >= ? LIMIT 1",
            (route, trip_type, bucket, since),
        ).fetchone()
    return row is not None


def record_alert(route: str, trip_type: str, price: float) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO alerts (route, trip_type, price_bucket, price, sent_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (route, trip_type, _price_bucket(price), price, _now().isoformat()),
        )
