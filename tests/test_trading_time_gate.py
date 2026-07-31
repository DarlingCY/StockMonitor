"""Tests for A-share market trading-time visibility gate."""
import unittest
from datetime import datetime

from stockmonitor.services.trading_time_gate import (
    is_trading_day,
    is_trading_time,
    is_visible,
)


class TradingTimeGateTests(unittest.TestCase):
    def test_trading_day(self) -> None:
        cases = [
            (datetime(2025, 1, 6, 10, 0), True),   # Monday
            (datetime(2025, 1, 10, 10, 0), True),  # Friday
            (datetime(2025, 1, 4, 10, 0), False),  # Saturday
            (datetime(2025, 1, 5, 10, 0), False),  # Sunday
            (datetime(2025, 1, 1, 10, 0), False),  # New Year holiday
            (datetime(2025, 10, 1, 10, 0), False), # National Day holiday
        ]
        for dt, expected in cases:
            with self.subTest(dt=dt):
                self.assertEqual(is_trading_day(dt), expected)

    def test_trading_time(self) -> None:
        day = datetime(2025, 1, 6)  # Monday
        cases = [
            (day.replace(hour=9, minute=30), True),
            (day.replace(hour=10, minute=0), True),
            (day.replace(hour=11, minute=29, second=59), True),
            (day.replace(hour=11, minute=30), False),
            (day.replace(hour=12, minute=0), False),
            (day.replace(hour=13, minute=0), True),
            (day.replace(hour=14, minute=59, second=59), True),
            (day.replace(hour=15, minute=0), False),
            (day.replace(hour=9, minute=25), False),
            (day.replace(hour=20, minute=0), False),
        ]
        for dt, expected in cases:
            with self.subTest(dt=dt):
                self.assertEqual(is_trading_time(dt), expected)

    def test_visible(self) -> None:
        cases = [
            (datetime(2025, 1, 6, 10, 30), True),   # weekday morning
            (datetime(2025, 1, 8, 14, 30), True),   # weekday afternoon
            (datetime(2025, 1, 6, 9, 30), True),    # morning open boundary
            (datetime(2025, 1, 6, 13, 0), True),    # afternoon open boundary
            (datetime(2025, 1, 6, 11, 30), False),  # lunch start
            (datetime(2025, 1, 6, 15, 0), False),   # close
            (datetime(2025, 1, 4, 10, 30), False),  # weekend
            (datetime(2025, 1, 1, 10, 30), False),  # holiday
            (datetime(2025, 1, 9, 9, 15), False),   # pre-open
            (datetime(2025, 1, 10, 15, 30), False), # post-close
        ]
        for dt, expected in cases:
            with self.subTest(dt=dt):
                self.assertEqual(is_visible(dt), expected)


if __name__ == "__main__":
    unittest.main()
