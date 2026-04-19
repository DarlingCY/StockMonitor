"""Tests for A-share market trading-time visibility gate.

Expected behavior: Show only when BOTH trading day AND trading time are true.
- Trading day: Monday-Friday
- Trading time windows: 09:30-11:30 and 13:00-15:00 local time
"""
import unittest
from datetime import datetime, time

# The module under test - expected API:
# from stockmonitor.services.trading_time_gate import (
#     is_trading_day,
#     is_trading_time,
#     is_visible,
# )


class TradingDayTests(unittest.TestCase):
    """Tests for is_trading_day function."""

    def test_monday_is_trading_day(self) -> None:
        """Monday should be a trading day."""
        from stockmonitor.services.trading_time_gate import is_trading_day

        # Monday, January 6, 2025
        dt = datetime(2025, 1, 6, 10, 0)
        self.assertTrue(is_trading_day(dt))

    def test_tuesday_is_trading_day(self) -> None:
        """Tuesday should be a trading day."""
        from stockmonitor.services.trading_time_gate import is_trading_day

        dt = datetime(2025, 1, 7, 10, 0)
        self.assertTrue(is_trading_day(dt))

    def test_wednesday_is_trading_day(self) -> None:
        """Wednesday should be a trading day."""
        from stockmonitor.services.trading_time_gate import is_trading_day

        dt = datetime(2025, 1, 8, 10, 0)
        self.assertTrue(is_trading_day(dt))

    def test_thursday_is_trading_day(self) -> None:
        """Thursday should be a trading day."""
        from stockmonitor.services.trading_time_gate import is_trading_day

        dt = datetime(2025, 1, 9, 10, 0)
        self.assertTrue(is_trading_day(dt))

    def test_friday_is_trading_day(self) -> None:
        """Friday should be a trading day."""
        from stockmonitor.services.trading_time_gate import is_trading_day

        dt = datetime(2025, 1, 10, 10, 0)
        self.assertTrue(is_trading_day(dt))

    def test_new_years_day_is_not_trading_day(self) -> None:
        """法定休市日不应视为交易日。"""
        from stockmonitor.services.trading_time_gate import is_trading_day

        dt = datetime(2025, 1, 1, 10, 0)
        self.assertFalse(is_trading_day(dt))

    def test_national_day_holiday_is_not_trading_day(self) -> None:
        """国庆休市日不应视为交易日。"""
        from stockmonitor.services.trading_time_gate import is_trading_day

        dt = datetime(2025, 10, 1, 10, 0)
        self.assertFalse(is_trading_day(dt))

    def test_saturday_is_not_trading_day(self) -> None:
        """Saturday should not be a trading day."""
        from stockmonitor.services.trading_time_gate import is_trading_day

        # Saturday, January 4, 2025
        dt = datetime(2025, 1, 4, 10, 0)
        self.assertFalse(is_trading_day(dt))

    def test_sunday_is_not_trading_day(self) -> None:
        """Sunday should not be a trading day."""
        from stockmonitor.services.trading_time_gate import is_trading_day

        # Sunday, January 5, 2025
        dt = datetime(2025, 1, 5, 10, 0)
        self.assertFalse(is_trading_day(dt))


class TradingTimeTests(unittest.TestCase):
    """Tests for is_trading_time function."""

    def test_morning_session_start_is_trading_time(self) -> None:
        """09:30 (morning session start) should be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 9, 30)
        self.assertTrue(is_trading_time(dt))

    def test_morning_session_mid_is_trading_time(self) -> None:
        """10:00 (mid morning session) should be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 10, 0)
        self.assertTrue(is_trading_time(dt))

    def test_morning_session_end_is_trading_time(self) -> None:
        """11:29 (just before morning close) should be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 11, 29, 59)
        self.assertTrue(is_trading_time(dt))

    def test_afternoon_session_start_is_trading_time(self) -> None:
        """13:00 (afternoon session start) should be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 13, 0)
        self.assertTrue(is_trading_time(dt))

    def test_afternoon_session_mid_is_trading_time(self) -> None:
        """14:00 (mid afternoon session) should be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 14, 0)
        self.assertTrue(is_trading_time(dt))

    def test_afternoon_session_end_is_trading_time(self) -> None:
        """14:59 (just before close) should be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 14, 59, 59)
        self.assertTrue(is_trading_time(dt))

    def test_pre_open_not_trading_time(self) -> None:
        """09:25 (pre-open) should not be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 9, 25)
        self.assertFalse(is_trading_time(dt))

    def test_early_pre_open_not_trading_time(self) -> None:
        """09:00 (early pre-open) should not be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 9, 0)
        self.assertFalse(is_trading_time(dt))

    def test_lunch_break_start_not_trading_time(self) -> None:
        """11:30 (lunch break start) should not be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 11, 30)
        self.assertFalse(is_trading_time(dt))

    def test_lunch_break_mid_not_trading_time(self) -> None:
        """12:00 (mid lunch break) should not be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 12, 0)
        self.assertFalse(is_trading_time(dt))

    def test_lunch_break_end_not_trading_time(self) -> None:
        """12:59 (just before afternoon open) should not be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 12, 59, 59)
        self.assertFalse(is_trading_time(dt))

    def test_post_close_not_trading_time(self) -> None:
        """15:00 (post-close) should not be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 15, 0)
        self.assertFalse(is_trading_time(dt))

    def test_late_post_close_not_trading_time(self) -> None:
        """16:00 (late post-close) should not be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 16, 0)
        self.assertFalse(is_trading_time(dt))

    def test_night_not_trading_time(self) -> None:
        """20:00 (night) should not be trading time."""
        from stockmonitor.services.trading_time_gate import is_trading_time

        dt = datetime(2025, 1, 6, 20, 0)
        self.assertFalse(is_trading_time(dt))


class VisibilityGateTests(unittest.TestCase):
    """Tests for is_visible function - the main visibility gate."""

    def test_weekday_morning_session_visible(self) -> None:
        """Weekday during morning trading session should be visible."""
        from stockmonitor.services.trading_time_gate import is_visible

        # Monday, January 6, 2025, 10:30
        dt = datetime(2025, 1, 6, 10, 30)
        self.assertTrue(is_visible(dt))

    def test_weekday_afternoon_session_visible(self) -> None:
        """Weekday during afternoon trading session should be visible."""
        from stockmonitor.services.trading_time_gate import is_visible

        # Wednesday, January 8, 2025, 14:30
        dt = datetime(2025, 1, 8, 14, 30)
        self.assertTrue(is_visible(dt))

    def test_weekend_not_visible(self) -> None:
        """Weekend should not be visible regardless of time."""
        from stockmonitor.services.trading_time_gate import is_visible

        # Saturday, January 4, 2025, 10:30 (would be trading time on weekday)
        dt = datetime(2025, 1, 4, 10, 30)
        self.assertFalse(is_visible(dt))

    def test_sunday_not_visible(self) -> None:
        """Sunday should not be visible regardless of time."""
        from stockmonitor.services.trading_time_gate import is_visible

        # Sunday, January 5, 2025, 14:00 (would be trading time on weekday)
        dt = datetime(2025, 1, 5, 14, 0)
        self.assertFalse(is_visible(dt))

    def test_weekday_lunch_break_not_visible(self) -> None:
        """Weekday during lunch break should not be visible."""
        from stockmonitor.services.trading_time_gate import is_visible

        # Tuesday, January 7, 2025, 11:45
        dt = datetime(2025, 1, 7, 11, 45)
        self.assertFalse(is_visible(dt))

    def test_weekday_pre_open_not_visible(self) -> None:
        """Weekday before market open should not be visible."""
        from stockmonitor.services.trading_time_gate import is_visible

        # Thursday, January 9, 2025, 09:15
        dt = datetime(2025, 1, 9, 9, 15)
        self.assertFalse(is_visible(dt))

    def test_weekday_post_close_not_visible(self) -> None:
        """Weekday after market close should not be visible."""
        from stockmonitor.services.trading_time_gate import is_visible

        # Friday, January 10, 2025, 15:30
        dt = datetime(2025, 1, 10, 15, 30)
        self.assertFalse(is_visible(dt))

    def test_holiday_during_trading_hours_not_visible(self) -> None:
        """法定休市日即使在交易时间段内也不显示。"""
        from stockmonitor.services.trading_time_gate import is_visible

        dt = datetime(2025, 1, 1, 10, 30)
        self.assertFalse(is_visible(dt))

    def test_weekday_early_morning_not_visible(self) -> None:
        """Weekday early morning should not be visible."""
        from stockmonitor.services.trading_time_gate import is_visible

        # Monday, January 6, 2025, 08:00
        dt = datetime(2025, 1, 6, 8, 0)
        self.assertFalse(is_visible(dt))

    def test_weekday_evening_not_visible(self) -> None:
        """Weekday evening should not be visible."""
        from stockmonitor.services.trading_time_gate import is_visible

        # Wednesday, January 8, 2025, 18:00
        dt = datetime(2025, 1, 8, 18, 0)
        self.assertFalse(is_visible(dt))

    def test_boundary_morning_session_start_visible(self) -> None:
        """Exactly 09:30 on weekday should be visible."""
        from stockmonitor.services.trading_time_gate import is_visible

        dt = datetime(2025, 1, 6, 9, 30, 0)
        self.assertTrue(is_visible(dt))

    def test_boundary_morning_session_end_not_visible(self) -> None:
        """Exactly 11:30 on weekday should not be visible (lunch break starts)."""
        from stockmonitor.services.trading_time_gate import is_visible

        dt = datetime(2025, 1, 6, 11, 30, 0)
        self.assertFalse(is_visible(dt))

    def test_boundary_afternoon_session_start_visible(self) -> None:
        """Exactly 13:00 on weekday should be visible."""
        from stockmonitor.services.trading_time_gate import is_visible

        dt = datetime(2025, 1, 6, 13, 0, 0)
        self.assertTrue(is_visible(dt))

    def test_boundary_afternoon_session_end_not_visible(self) -> None:
        """Exactly 15:00 on weekday should not be visible (market closed)."""
        from stockmonitor.services.trading_time_gate import is_visible

        dt = datetime(2025, 1, 6, 15, 0, 0)
        self.assertFalse(is_visible(dt))


if __name__ == "__main__":
    unittest.main()
