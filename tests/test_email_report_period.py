"""Tests for email report period formatting in EmailService."""

import unittest
from datetime import datetime

import src.services.email_service as email_module
from src.services.email_service import EmailService


def _clear_report_period():
    email_module._current_report_start = None
    email_module._current_report_end = None


class TestEmailReportPeriod(unittest.TestCase):
    def tearDown(self):
        _clear_report_period()

    def setUp(self):
        _clear_report_period()

    def test_single_day_period(self):
        start = datetime(2026, 5, 26, 0, 0, 0)
        end = datetime(2026, 5, 26, 23, 59, 59)
        EmailService.set_report_period(start, end)
        self.assertEqual(EmailService._format_report_period(), '26/05/2026')
        self.assertEqual(
            EmailService._get_report_title_with_date('Daily Report'),
            'Daily Report - 26/05/2026'
        )

    def test_monthly_range_period(self):
        start = datetime(2026, 1, 1, 0, 0, 0)
        end = datetime(2026, 1, 31, 23, 59, 59)
        EmailService.set_report_period(start, end)
        self.assertEqual(
            EmailService._format_report_period(),
            '01/01/2026 - 31/01/2026'
        )

    def test_weekly_range_period(self):
        start = datetime(2026, 5, 18, 0, 0, 0)  # Sunday
        end = datetime(2026, 5, 24, 23, 59, 59)  # Saturday
        EmailService.set_report_period(start, end)
        self.assertEqual(
            EmailService._format_report_period(),
            '18/05/2026 - 24/05/2026'
        )

    def test_no_period_set(self):
        self.assertIsNone(EmailService._format_report_period())
        self.assertEqual(
            EmailService._get_report_title_with_date('Report'),
            'Report'
        )


if __name__ == '__main__':
    unittest.main()
