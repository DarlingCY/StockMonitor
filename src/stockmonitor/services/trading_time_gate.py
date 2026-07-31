"""A-share market trading-time visibility gate."""
from __future__ import annotations

from datetime import datetime, time

import cn_stock_holidays.data as shsz

_MORNING = (time(9, 30, 0), time(11, 30, 0))
_AFTERNOON = (time(13, 0, 0), time(15, 0, 0))


def is_trading_day(dt: datetime) -> bool:
    return shsz.is_trading_day(dt.date())


def is_trading_time(dt: datetime) -> bool:
    t = dt.time()
    return (_MORNING[0] <= t < _MORNING[1]) or (_AFTERNOON[0] <= t < _AFTERNOON[1])


def is_visible(dt: datetime) -> bool:
    return is_trading_day(dt) and is_trading_time(dt)
