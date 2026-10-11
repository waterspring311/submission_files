from datetime import date, datetime, time


def first_present(data, *keys, default=None):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def parse_datetime(value):
    if value in (None, ""):
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                pass
    return datetime.utcnow()


def parse_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def parse_time(value):
    if value in (None, ""):
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        return time.fromisoformat(value)
    return value
