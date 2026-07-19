"""Логика определения "билет сильно дешевле обычного".

Билет считается выгодным, если выполнено любое из условий:
  * есть достаточная история и цена <= median * (1 - DROP_THRESHOLD); либо
  * цена <= абсолютного порога направления (hard_cap) — срабатывает даже без
    накопленной истории, чтобы уведомления шли с первых дней.
"""
from __future__ import annotations

from dataclasses import dataclass

import config
import storage
from api import Ticket
from routes import Destination


@dataclass
class Deal:
    destination: Destination
    ticket: Ticket
    trip_type: str            # "round_trip" | "one_way"
    price: float
    median: float | None      # обычная цена (медиана), если известна
    discount_pct: int | None  # на сколько % ниже медианы, если известна


def _evaluate(dest: Destination, ticket: Ticket | None, trip_type: str,
              hard_cap: int) -> Deal | None:
    if ticket is None:
        return None

    route = f"{ticket.origin}-{ticket.destination}"
    price = ticket.price

    median = storage.baseline_median(route, trip_type)
    discount_pct = None
    is_cheap = False

    if median is not None:
        discount_pct = int(round((1 - price / median) * 100))
        if price <= median * (1 - config.DROP_THRESHOLD):
            is_cheap = True

    if price <= hard_cap:
        is_cheap = True

    if not is_cheap:
        return None

    return Deal(
        destination=dest,
        ticket=ticket,
        trip_type=trip_type,
        price=price,
        median=median,
        discount_pct=discount_pct,
    )


def find_deal(dest: Destination, round_trip: Ticket | None,
              one_way: Ticket | None) -> Deal | None:
    """Проверить билеты направления. Приоритет — туда-обратно.

    Если туда-обратно не выгоден (или отсутствует), проверяем в одну сторону.
    Возвращает выгодное предложение или None.
    """
    rt_deal = _evaluate(dest, round_trip, "round_trip", dest.hard_cap_rt)
    if rt_deal is not None:
        return rt_deal
    return _evaluate(dest, one_way, "one_way", dest.hard_cap_ow)
