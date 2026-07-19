"""Конфигурация монитора авиабилетов.

Секреты берутся из переменных окружения (файл .env), а пороги/интервалы заданы
константами ниже — их удобно править под себя.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Секреты (из .env) -----------------------------------------------------
TRAVELPAYOUTS_TOKEN = os.getenv("TRAVELPAYOUTS_TOKEN", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Получателей уведомлений может быть несколько — перечислите их chat_id через
# запятую, например:  TELEGRAM_CHAT_ID=12345678,87654321
TELEGRAM_CHAT_IDS = [
    c.strip() for c in TELEGRAM_CHAT_ID.replace(";", ",").split(",") if c.strip()
]

# --- Параметры поиска ------------------------------------------------------
ORIGIN = "SVX"                 # Екатеринбург (Кольцово)
CURRENCY = "rub"
MONTHS_AHEAD = 2               # на сколько месяцев вперёд смотрим
TRIP_DURATION_DAYS = 14        # желаемая длительность поездки (туда-обратно)
TRIP_DURATION_TOLERANCE = 3    # допуск ± дней вокруг желаемой длительности

# --- Логика "дешёвый билет" ------------------------------------------------
DROP_THRESHOLD = 0.25          # на сколько ниже медианы = "сильно дешевле" (25%)
BASELINE_WINDOW_DAYS = 21      # окно истории для расчёта обычной цены
MIN_OBSERVATIONS = 5           # минимум наблюдений, чтобы доверять медиане

# --- Антиспам --------------------------------------------------------------
ALERT_COOLDOWN_HOURS = 12      # не слать одно и то же чаще, чем раз в N часов
PRICE_BUCKET_SIZE = 500        # шаг "ценового бакета" для дедупликации (руб.)

# --- Прочее ----------------------------------------------------------------
CHECK_INTERVAL_SECONDS = 1800  # интервал между полными прогонами (30 минут)
REQUEST_DELAY_SECONDS = 0.3    # пауза между запросами к API (вежливость)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "prices.db")
AVIASALES_BASE_URL = "https://www.aviasales.ru"


def validate() -> list[str]:
    """Возвращает список отсутствующих обязательных секретов."""
    missing = []
    if not TRAVELPAYOUTS_TOKEN:
        missing.append("TRAVELPAYOUTS_TOKEN")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_IDS:
        missing.append("TELEGRAM_CHAT_ID")
    return missing
