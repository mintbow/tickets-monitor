"""Отправка уведомлений в Telegram через Bot API."""
from __future__ import annotations

import html

import requests

import config
from detector import Deal

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

TRIP_TYPE_RU = {
    "round_trip": "Туда-обратно",
    "one_way": "В одну сторону",
}


def _send(text: str) -> bool:
    url = TELEGRAM_API.format(token=config.TELEGRAM_BOT_TOKEN)
    try:
        resp = requests.post(url, data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        }, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok"):
            print(f"[telegram] ошибка: {payload}")
            return False
        return True
    except (requests.RequestException, ValueError) as exc:
        print(f"[telegram] ошибка отправки: {exc}")
        return False


def send_test_message() -> bool:
    return _send("✅ Тест: монитор авиабилетов подключён к Telegram.")


def _format_price(price: float) -> str:
    return f"{int(round(price)):,}".replace(",", " ")


def notify_deal(deal: Deal) -> bool:
    d = deal.destination
    t = deal.ticket
    trip_ru = TRIP_TYPE_RU.get(deal.trip_type, deal.trip_type)

    lines = [
        f"✈️ <b>Дешёвый билет!</b> {html.escape(d.city)} "
        f"({html.escape(d.country)})",
        f"Маршрут: {config.ORIGIN} → {t.destination} · {trip_ru}",
        f"Цена: <b>{_format_price(deal.price)} ₽</b>",
    ]

    if deal.median is not None and deal.discount_pct is not None:
        lines.append(
            f"Обычно ~{_format_price(deal.median)} ₽ "
            f"(на {deal.discount_pct}% дешевле)"
        )

    if t.return_date:
        dur = t.duration_days
        dur_str = f", {dur} дн." if dur is not None else ""
        lines.append(f"Даты: {t.depart_date} → {t.return_date}{dur_str}")
    else:
        lines.append(f"Вылет: {t.depart_date}")

    if t.transfers is not None:
        lines.append("Пересадки: " +
                     ("прямой" if t.transfers == 0 else str(t.transfers)))

    if t.link:
        lines.append(f'<a href="{html.escape(t.link)}">Открыть на Aviasales</a>')

    return _send("\n".join(lines))
