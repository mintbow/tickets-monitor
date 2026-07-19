"""Монитор дешёвых авиабилетов из Екатеринбурга.

Запуск:
  python main.py                # непрерывный цикл (проверка раз в час)
  python main.py --once         # один прогон и выход
  python main.py --test-notify  # отправить тестовое сообщение в Telegram
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

import config
import notifier
import storage
from api import TravelpayoutsClient, Ticket
from detector import find_deal
from routes import DESTINATIONS, Destination


def _log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def _price(t: Ticket | None) -> str:
    return f"{int(t.price)} ₽" if t else "нет данных"


def _process_destination(client: TravelpayoutsClient, dest: Destination) -> None:
    route = f"{config.ORIGIN}-{dest.code}"

    round_trip = client.cheapest_round_trip(dest.code)
    one_way = client.cheapest_one_way(dest.code)

    _log(f"{dest.city} ({route}): туда-обратно {_price(round_trip)}, "
         f"в одну сторону {_price(one_way)}")

    # Сохраняем наблюдения для истории/медианы.
    if round_trip:
        storage.record_observation(route, "round_trip", round_trip.price,
                                   round_trip.depart_date, round_trip.return_date,
                                   round_trip.link)
    if one_way:
        storage.record_observation(route, "one_way", one_way.price,
                                   one_way.depart_date, None, one_way.link)

    deal = find_deal(dest, round_trip, one_way)
    if deal is None:
        return

    if storage.recently_alerted(route, deal.trip_type, deal.price):
        _log(f"  -> выгодно ({int(deal.price)} ₽), но недавно уже уведомляли — пропуск")
        return

    _log(f"  -> ВЫГОДНО: {int(deal.price)} ₽ ({deal.trip_type}) — шлём уведомление")
    if notifier.notify_deal(deal):
        storage.record_alert(route, deal.trip_type, deal.price)


def run_once(client: TravelpayoutsClient) -> None:
    for dest in DESTINATIONS:
        try:
            _process_destination(client, dest)
        except Exception as exc:  # один сбойный маршрут не должен ронять весь прогон
            _log(f"ошибка при обработке {dest.city}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Монитор дешёвых авиабилетов")
    parser.add_argument("--once", action="store_true",
                        help="сделать один прогон и выйти")
    parser.add_argument("--test-notify", action="store_true",
                        help="отправить тестовое сообщение в Telegram и выйти")
    args = parser.parse_args()

    missing = config.validate()
    if missing:
        _log("Не заданы обязательные переменные окружения: " + ", ".join(missing))
        _log("Скопируйте .env.example в .env и заполните значения.")
        return 1

    storage.init_db()

    if args.test_notify:
        ok = notifier.send_test_message()
        _log("Тестовое сообщение отправлено." if ok else "Не удалось отправить.")
        return 0 if ok else 1

    client = TravelpayoutsClient(config.TRAVELPAYOUTS_TOKEN, config.CURRENCY)

    if args.once:
        _log("Одиночный прогон...")
        run_once(client)
        _log("Готово.")
        return 0

    _log(f"Запуск мониторинга. Направлений: {len(DESTINATIONS)}. "
         f"Интервал: {config.CHECK_INTERVAL_SECONDS} с.")
    while True:
        run_once(client)
        _log(f"Цикл завершён. Спим {config.CHECK_INTERVAL_SECONDS} с.")
        try:
            time.sleep(config.CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            _log("Остановлено пользователем.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
