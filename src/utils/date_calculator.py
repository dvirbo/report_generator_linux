"""
Date Calculator
Calculate date ranges based on interval types
"""

from datetime import datetime, date, timedelta
from typing import Tuple

ALLOWED_INTERVALS = {
    'bi-daily',
    'daily',
    'weekly',
    'monthly',
    'quarterly',
    'yearly',
    'yesterday',
}


def validate_interval_name(interval_name: str) -> bool:
    """
    Validate interval name against allowed intervals.
    
    >>> validate_interval_name('daily')
    True
    >>> validate_interval_name('DAILY')
    True
    >>> validate_interval_name('  daily  ')
    True
    >>> validate_interval_name('bi-daily')
    True
    >>> validate_interval_name('invalid')
    False
    >>> validate_interval_name('')
    False
    >>> validate_interval_name(None)
    False
    """
    return (interval_name or '').strip().lower() in ALLOWED_INTERVALS


class DateCalculator:
    """
    Calculate date/time ranges for report intervals based on an input date.
    
    >>> from datetime import datetime
    >>> calc = DateCalculator()
    >>> 
    >>> # Test daily interval with 2025-01-01
    >>> base_dt = datetime(2025, 1, 1, 12, 0, 0)
    >>> start, end = calc.calculate_date_range_by_name('daily', base_dt)
    >>> start == datetime(2025, 1, 1, 0, 0, 0)
    True
    >>> end == datetime(2025, 1, 1, 23, 59, 59, 999999)
    True
    >>> 
    >>> # Test bi-daily interval - first half (before noon)
    >>> morning_dt = datetime(2025, 1, 1, 10, 0, 0)
    >>> start, end = calc.calculate_date_range_by_name('bi-daily', morning_dt)
    >>> start == datetime(2025, 1, 1, 0, 0, 0)
    True
    >>> end == datetime(2025, 1, 1, 11, 59, 59)
    True
    >>> 
    >>> # Test bi-daily interval - second half (after noon)
    >>> afternoon_dt = datetime(2025, 1, 1, 14, 0, 0)
    >>> start, end = calc.calculate_date_range_by_name('bi-daily', afternoon_dt)
    >>> start == datetime(2025, 1, 1, 12, 0, 0)
    True
    >>> end == datetime(2025, 1, 1, 23, 59, 59)
    True
    >>> 
    >>> # Test weekly interval
    >>> start, end = calc.calculate_date_range_by_name('weekly', base_dt)
    >>> start.date() == date(2025, 1, 1)
    True
    >>> end.date() == date(2025, 1, 7)
    True
    >>> 
    >>> # Test monthly interval
    >>> start, end = calc.calculate_date_range_by_name('monthly', base_dt)
    >>> start.date() == date(2025, 1, 1)
    True
    >>> end.date() == date(2025, 1, 31)
    True
    >>> 
    >>> # Test quarterly interval (Q1)
    >>> start, end = calc.calculate_date_range_by_name('quarterly', base_dt)
    >>> start.date() == date(2025, 1, 1)
    True
    >>> end.date() == date(2025, 3, 31)
    True
    >>> 
    >>> # Test invalid interval
    >>> try:
    ...     calc.calculate_date_range_by_name('invalid', base_dt)
    ... except ValueError as e:
    ...     'Invalid interval name' in str(e)
    True
    """

    @staticmethod
    def calculate_date_range_by_name(interval_name: str, base_datetime: datetime) -> Tuple[datetime, datetime]:
        name = (interval_name or '').strip().lower()
        if name not in ALLOWED_INTERVALS:
            raise ValueError(f"Invalid interval name: {interval_name}")

        if name == 'bi-daily':
            return DateCalculator._range_bidaily_by_cutoff(base_datetime)
        if name == 'daily' or name == 'last_bd':
            return DateCalculator._full_day(base_datetime.date())
        if name == 'weekly':
            week_start = base_datetime.date()
            week_end = week_start + timedelta(days=6)
            return DateCalculator._range_dates(week_start, week_end)
        if name == 'monthly':
            start = date(base_datetime.year, base_datetime.month, 1)
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
            return DateCalculator._range_dates(start, end)
        if name == 'quarterly':
            start = base_datetime.date()
            end = DateCalculator._quarter_end_from_start(start)
            return DateCalculator._range_dates(start, end)

        raise ValueError(f"Unhandled interval: {interval_name}")

    @staticmethod
    def _range_bidaily_by_cutoff(now_dt: datetime) -> Tuple[datetime, datetime]:
        """
        Calculate bi-daily range split at noon:
        - First half: 12:00 AM (midnight) - 11:59 AM
        - Second half: 12:00 PM (noon) - 11:59 PM
        """
        cutoff = now_dt.replace(hour=12, minute=0, second=0, microsecond=0).time()
        exec_time = now_dt.time()
        day = now_dt.date()
        
        if exec_time < cutoff:
            # First half: midnight to 11:59 AM
            start = datetime.combine(day, datetime.min.time())
            end = datetime.combine(day, datetime.min.time()).replace(hour=11, minute=59, second=59)
        else:
            # Second half: noon to 11:59 PM
            start = datetime.combine(day, datetime.min.time()).replace(hour=12, minute=0, second=0)
            end = datetime.combine(day, datetime.min.time()).replace(hour=23, minute=59, second=59)
        return start, end

    @staticmethod
    def _full_day(d: date) -> Tuple[datetime, datetime]:
        return datetime.combine(d, datetime.min.time()), datetime.combine(d, datetime.max.time())

    @staticmethod
    def _range_dates(start_date: date, end_date: date) -> Tuple[datetime, datetime]:
        return datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())

    @staticmethod
    def _quarter_end_from_start(q_start: date) -> date:
        m = q_start.month
        if m in (1, 2, 3):
            return date(q_start.year, 3, 31)
        if m in (4, 5, 6):
            return date(q_start.year, 6, 30)
        if m in (7, 8, 9):
            return date(q_start.year, 9, 30)
        return date(q_start.year, 12, 31)



