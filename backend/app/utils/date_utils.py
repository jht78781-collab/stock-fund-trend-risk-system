from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


CHINA_TZ = ZoneInfo("Asia/Shanghai")


def china_now() -> datetime:
    return datetime.now(CHINA_TZ)


def default_start_date(days: int = 365) -> date:
    return china_now().date() - timedelta(days=days)


def normalize_akshare_date(value: str | None, fallback: date) -> str:
    if not value:
        return fallback.strftime("%Y%m%d")

    stripped = value.strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(stripped, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    raise ValueError("日期格式必须为 YYYY-MM-DD 或 YYYYMMDD")


def parse_trade_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None

