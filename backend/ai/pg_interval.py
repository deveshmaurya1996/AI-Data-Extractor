
from __future__ import annotations

from typing import Optional

_DEFAULT = "INTERVAL '30 days'"
_UNIT = {"days": "day", "weeks": "week", "months": "month"}


def interval_sql(period: Optional[str]) -> str:
    if not period:
        return _DEFAULT
    parts = period.split("_", 1)
    if len(parts) != 2:
        return _DEFAULT
    num_s, plural = parts[0], parts[1]
    try:
        n = int(num_s)
    except ValueError:
        return _DEFAULT
    unit = _UNIT.get(plural)
    if unit is None:
        return _DEFAULT
    return f"INTERVAL '{n} {unit}'"
