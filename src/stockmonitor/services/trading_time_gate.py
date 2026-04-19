"""A-share market trading-time visibility gate."""
from __future__ import annotations

from datetime import datetime, time

import cn_stock_holidays.data as shsz


def is_trading_day(dt: datetime) -> bool:
    """Check whether the given datetime falls on a real A-share trading day."""
    return shsz.is_trading_day(dt.date())


def is_trading_time(dt: datetime) -> bool:
    """Check if the given datetime falls within A-share trading hours.

    Trading time windows:
    - Morning session: 09:30:00 - 11:29:59 (inclusive of start, exclusive of end)
    - Afternoon session: 13:00:00 - 14:59:59 (inclusive of start, exclusive of end)

    Args:
        dt: The datetime to check.

    Returns:
        True if the time is within trading hours, False otherwise.
    """
    t = dt.time()

    # Morning session: 09:30 - 11:30 (exclusive at end)
    morning_start = time(9, 30, 0)
    morning_end = time(11, 30, 0)

    # Afternoon session: 13:00 - 15:00 (exclusive at end)
    afternoon_start = time(13, 0, 0)
    afternoon_end = time(15, 0, 0)

    return (morning_start <= t < morning_end) or (afternoon_start <= t < afternoon_end)


def is_visible(dt: datetime) -> bool:
    """Check if the A-share market should be visible at the given datetime.

    Visibility requires BOTH conditions to be true:
    1. It is a trading day (Monday-Friday)
    2. It is within trading hours (09:30-11:30 or 13:00-15:00)

    Args:
        dt: The datetime to check.

    Returns:
        True if the market should be visible, False otherwise.
    """
    return is_trading_day(dt) and is_trading_time(dt)
