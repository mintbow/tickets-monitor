"""Клиент официального Travelpayouts / Aviasales Data API.

Используется endpoint prices_for_dates — он отдаёт кэшированные цены реальных
поисков (самые дешёвые билеты по датам), что и нужно для мониторинга.
Документация: https://support.travelpayouts.com/hc/en-us/articles/203956163
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime

import requests

import config

API_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


@dataclass
class Ticket:
    origin: str
    destination: str
    price: float
    depart_date: str          # ISO дата вылета (YYYY-MM-DD)
    return_date: str | None   # ISO дата возврата или None для one-way
    link: str                 # полная ссылка на бронирование
    airline: str | None = None
    transfers: int | None = None

    @property
    def duration_days(self) -> int | None:
        if not self.return_date:
            return None
        d1 = date.fromisoformat(self.depart_date)
        d2 = date.fromisoformat(self.return_date)
        return (d2 - d1).days


def _iso_date(value: str | None) -> str | None:
    """Из '2026-08-10T13:45:00+05:00' -> '2026-08-10'."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        # На случай, если API вернёт уже 'YYYY-MM-DD'
        return value[:10]


def _months_ahead(n: int) -> list[str]:
    """Список ближайших n месяцев в формате YYYY-MM, начиная с текущего."""
    today = date.today()
    months = []
    year, month = today.year, today.month
    for _ in range(n):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


class TravelpayoutsClient:
    def __init__(self, token: str, currency: str = "rub"):
        self.token = token
        self.currency = currency
        self.session = requests.Session()

    def _fetch(self, destination: str, month: str, one_way: bool) -> list[Ticket]:
        params = {
            "origin": config.ORIGIN,
            "destination": destination,
            "departure_at": month,
            "currency": self.currency,
            "one_way": "true" if one_way else "false",
            "sorting": "price",
            "limit": 1000,
            "page": 1,
            "token": self.token,
        }
        try:
            resp = self.session.get(API_URL, params=params, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"[api] ошибка запроса {destination} {month} "
                  f"({'OW' if one_way else 'RT'}): {exc}")
            return []

        if not payload.get("success", False):
            print(f"[api] неуспешный ответ {destination} {month}: "
                  f"{payload.get('error') or payload}")
            return []

        tickets: list[Ticket] = []
        for item in payload.get("data", []):
            price = item.get("price")
            depart = _iso_date(item.get("departure_at"))
            if price is None or depart is None:
                continue
            link = item.get("link", "")
            if link.startswith("/"):
                link = config.AVIASALES_BASE_URL + link
            tickets.append(Ticket(
                origin=item.get("origin", config.ORIGIN),
                destination=item.get("destination", destination),
                price=float(price),
                depart_date=depart,
                return_date=None if one_way else _iso_date(item.get("return_at")),
                link=link,
                airline=item.get("airline"),
                transfers=item.get("transfers"),
            ))
        time.sleep(config.REQUEST_DELAY_SECONDS)
        return tickets

    def cheapest_round_trip(self, destination: str) -> Ticket | None:
        """Самый дешёвый билет туда-обратно с длительностью ~TRIP_DURATION_DAYS."""
        target = config.TRIP_DURATION_DAYS
        tol = config.TRIP_DURATION_TOLERANCE
        best: Ticket | None = None
        for month in _months_ahead(config.MONTHS_AHEAD):
            for t in self._fetch(destination, month, one_way=False):
                dur = t.duration_days
                if dur is None or abs(dur - target) > tol:
                    continue
                if best is None or t.price < best.price:
                    best = t
        return best

    def cheapest_one_way(self, destination: str) -> Ticket | None:
        """Самый дешёвый билет в одну сторону."""
        best: Ticket | None = None
        for month in _months_ahead(config.MONTHS_AHEAD):
            for t in self._fetch(destination, month, one_way=True):
                if best is None or t.price < best.price:
                    best = t
        return best
