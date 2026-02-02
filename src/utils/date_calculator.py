"""
Date Calculator
Calculate date ranges based on interval types
"""

from datetime import datetime, date, timedelta
from typing import Tuple

ALLOWED_INTERVALS = {
    'last_bd',
    'bi-daily',
    'daily',
    'weekly',
    'monthly',
    'quarterly',
    'yearly',
}


def validate_interval_name(interval_name: str) -> bool:
    """
    Validate interval name against allowed intervals.
    """
    return (interval_name or '').strip().lower() in ALLOWED_INTERVALS


class DateCalculator:
    """
    Calculate date/time ranges for report intervals based on an input date.
    """

    @staticmethod
    def calculate_date_range_by_name(interval_name: str, base_datetime: datetime) -> Tuple[datetime, datetime]:
        name = (interval_name or '').strip().lower()
        if name not in ALLOWED_INTERVALS:
            raise ValueError(f"Invalid interval name: {interval_name}")

        if name == 'bi-daily':
            # Bi-daily splits day at 13:30 (1:30 PM)
            # First half: 00:00:00 to 13:30:00
            # Second half: 13:31:00 to 23:59:59.999999
            return DateCalculator._range_bidaily_by_cutoff(base_datetime)
        if name == 'daily' or name == 'last_bd':
            return DateCalculator._full_day(base_datetime.date())
        if name == 'weekly':
            # Calculate previous week (Sunday to Saturday)
            # Shell runs on first day of week (Sunday) or day after (Monday)
            return DateCalculator._previous_week(base_datetime.date())
        if name == 'monthly':
            # Calculate previous month (complete month)
            # Shell runs a few days after end of month
            return DateCalculator._previous_month(base_datetime.date())
        if name == 'quarterly':
            # Calculate previous quarter (complete quarter)
            # Shell runs after quarter ends
            return DateCalculator._previous_quarter(base_datetime.date())
        if name == 'yearly':
            # Calculate previous year (complete year)
            # Shell runs after year ends
            return DateCalculator._previous_year(base_datetime.date())

        raise ValueError(f"Unhandled interval: {interval_name}")

    @staticmethod
    def _range_bidaily_by_cutoff(now_dt: datetime) -> Tuple[datetime, datetime]:
        """
        Calculate bi-daily range split at 13:30 (1:30 PM):
        - First half: 00:00:00 to 13:30:00
        - Second half: 13:31:00 to 23:59:59.999999
        """
        cutoff_time = now_dt.replace(hour=13, minute=30, second=0, microsecond=0).time()
        exec_time = now_dt.time()
        day = now_dt.date()
        
        if exec_time <= cutoff_time:
            # First half: midnight to 13:30:00
            start = datetime.combine(day, datetime.min.time())
            end = datetime.combine(day, datetime.min.time()).replace(hour=13, minute=30, second=0, microsecond=0)
        else:
            # Second half: 13:31:00 to end of day
            start = datetime.combine(day, datetime.min.time()).replace(hour=13, minute=31, second=0, microsecond=0)
            end = datetime.combine(day, datetime.max.time())
        return start, end

    @staticmethod
    def _full_day(d: date) -> Tuple[datetime, datetime]:
        """
        Return full day range: 00:00:00 to 23:59:59.999999
        """
        return datetime.combine(d, datetime.min.time()), datetime.combine(d, datetime.max.time())

    @staticmethod
    def _range_dates(start_date: date, end_date: date) -> Tuple[datetime, datetime]:
        """
        Return date range covering full days from start_date to end_date
        """
        return datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())

    @staticmethod
    def _previous_week(base_date: date) -> Tuple[datetime, datetime]:
        """
        Calculate previous week (Sunday to Saturday).
        Shell runs on first day of week (Sunday) or day after (Monday).
        Returns the complete previous week.
        """
        # Get the weekday (0=Monday, 1=Tuesday, ..., 5=Saturday, 6=Sunday)
        weekday = base_date.weekday()
        
        # Calculate how many days to go back to get to previous Saturday (end of previous week)
        # Formula: (weekday + 2) % 7, but if result is 0 (Saturday), use 7
        days_to_previous_saturday = (weekday + 2) % 7
        if days_to_previous_saturday == 0:
            days_to_previous_saturday = 7
        
        # Previous Saturday (end of previous week)
        previous_saturday = base_date - timedelta(days=days_to_previous_saturday)
        
        # Previous Sunday (6 days before previous Saturday, start of previous week)
        previous_sunday = previous_saturday - timedelta(days=6)
        
        return DateCalculator._range_dates(previous_sunday, previous_saturday)

    @staticmethod
    def _previous_month(base_date: date) -> Tuple[datetime, datetime]:
        """
        Calculate previous month (complete month).
        Shell runs a few days after end of month.
        Returns the complete previous month (1st to last day).
        """
        # Get first day of current month
        first_of_current = date(base_date.year, base_date.month, 1)
        
        # Last day of previous month is one day before first of current
        last_of_previous = first_of_current - timedelta(days=1)
        
        # First day of previous month
        first_of_previous = date(last_of_previous.year, last_of_previous.month, 1)
        
        return DateCalculator._range_dates(first_of_previous, last_of_previous)

    @staticmethod
    def _previous_quarter(base_date: date) -> Tuple[datetime, datetime]:
        """
        Calculate previous quarter (complete quarter).
        Shell runs after quarter ends.
        Returns the complete previous quarter.
        """
        # Determine current quarter
        current_month = base_date.month
        
        if current_month in (1, 2, 3):
            # Current quarter is Q1, previous is Q4 of last year
            prev_quarter_start = date(base_date.year - 1, 10, 1)
            prev_quarter_end = date(base_date.year - 1, 12, 31)
        elif current_month in (4, 5, 6):
            # Current quarter is Q2, previous is Q1 of current year
            prev_quarter_start = date(base_date.year, 1, 1)
            prev_quarter_end = date(base_date.year, 3, 31)
        elif current_month in (7, 8, 9):
            # Current quarter is Q3, previous is Q2 of current year
            prev_quarter_start = date(base_date.year, 4, 1)
            prev_quarter_end = date(base_date.year, 6, 30)
        else:  # 10, 11, 12
            # Current quarter is Q4, previous is Q3 of current year
            prev_quarter_start = date(base_date.year, 7, 1)
            prev_quarter_end = date(base_date.year, 9, 30)
        
        return DateCalculator._range_dates(prev_quarter_start, prev_quarter_end)

    @staticmethod
    def _previous_year(base_date: date) -> Tuple[datetime, datetime]:
        """
        Calculate previous year (complete year).
        Shell runs after year ends.
        Returns the complete previous year (Jan 1 to Dec 31).
        """
        prev_year = base_date.year - 1
        prev_year_start = date(prev_year, 1, 1)
        prev_year_end = date(prev_year, 12, 31)
        
        return DateCalculator._range_dates(prev_year_start, prev_year_end)



