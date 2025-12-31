from __future__ import annotations
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore


IST = timezone(timedelta(hours=5, minutes=30))


def local_to_utc_iso(datetime_local: str, tz: str) -> str:
    """
    Input:  datetime_local like "2025-12-31T10:30:00"
            tz like "Asia/Kolkata"
    Output: "YYYY-MM-DDTHH:MM:SSZ" in UTC
    """

    # parse local datetime (naive)
    dt_local = datetime.fromisoformat(datetime_local)

    # attach timezone
    tzinfo = None
    if ZoneInfo is not None:
        try:
            tzinfo = ZoneInfo(tz)
        except Exception:
            tzinfo = None

    if tzinfo is None:
        # fallback: if tz is Asia/Kolkata (or anything fails), use IST offset
        tzinfo = IST

    dt_local = dt_local.replace(tzinfo=tzinfo)

    # convert to UTC
    dt_utc = dt_local.astimezone(timezone.utc)

    # return ISO with Z
    return dt_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
