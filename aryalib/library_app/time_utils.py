from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from library_app.config import APP_TIMEZONE


UTC = timezone.utc
try:
    LOCAL_TIMEZONE = ZoneInfo(APP_TIMEZONE)
except ZoneInfoNotFoundError:
    LOCAL_TIMEZONE = UTC


def now_local():
    return datetime.now(LOCAL_TIMEZONE)


def today_local():
    return now_local().date()


def current_date_text():
    return today_local().isoformat()


def current_time_text():
    return now_local().strftime("%H:%M:%S")


def parse_local_timestamp(date_text, time_text):
    if not date_text or not time_text:
        return None
    try:
        parsed = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return parsed.replace(tzinfo=LOCAL_TIMEZONE)


def now_utc():
    return datetime.now(UTC)
