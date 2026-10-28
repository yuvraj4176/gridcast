# -*- coding: utf-8 -*-
"""
Holiday utilities for GridCast.
Uses the python 'holidays' library for US/MA holidays.
No online API calls.
"""
import holidays as holidays_lib
from datetime import date


# Pre-build a large range of US/MA holidays
_us_holidays = holidays_lib.US(subdiv="MA", years=range(2020, 2031))


def is_holiday(d: date) -> bool:
    """Check if a date is a US/MA holiday."""
    return d in _us_holidays


def get_holiday_name(d: date) -> str | None:
    """Get the holiday name for a date, or None if not a holiday."""
    return _us_holidays.get(d, None)
