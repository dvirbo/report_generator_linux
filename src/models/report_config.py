"""
Report Configuration Model
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ReportConfig:
    """
    Report configuration model
    
    >>> config = ReportConfig(
    ...     report_id=1,
    ...     report_name='Test Report',
    ...     sql_query='SELECT * FROM table WHERE date BETWEEN :start_date AND :end_date',
    ...     interval='daily',
    ...     distribution_list='user1@example.com, user2@example.com',
    ...     bu_indicator='mador',
    ...     mail_subject='Test Subject',
    ...     mail_body='Test Body'
    ... )
    >>> config.report_id
    1
    >>> config.interval
    'daily'
    >>> 
    >>> # Test distribution list parsing
    >>> emails = config.get_distribution_list_emails()
    >>> len(emails)
    2
    >>> 'user1@example.com' in emails
    True
    >>> 'user2@example.com' in emails
    True
    >>> 
    >>> # Test empty distribution list
    >>> config_empty = ReportConfig(
    ...     report_id=2,
    ...     report_name='Empty List',
    ...     sql_query='SELECT * FROM table',
    ...     interval='daily',
    ...     distribution_list=None,
    ...     bu_indicator='mador',
    ...     mail_subject=None,
    ...     mail_body=None
    ... )
    >>> config_empty.get_distribution_list_emails()
    []
    >>> 
    >>> # Test requires_bu_parameter
    >>> config.requires_bu_parameter()
    False
    >>> 
    >>> config_branches = ReportConfig(
    ...     report_id=3,
    ...     report_name='Branches Report',
    ...     sql_query='SELECT * FROM table WHERE bu = :bu',
    ...     interval='daily',
    ...     distribution_list=None,
    ...     bu_indicator='branches',
    ...     mail_subject=None,
    ...     mail_body=None
    ... )
    >>> config_branches.requires_bu_parameter()
    True
    >>> 
    >>> config_merchav = ReportConfig(
    ...     report_id=4,
    ...     report_name='Merchav Report',
    ...     sql_query='SELECT * FROM table WHERE bu = :bu',
    ...     interval='daily',
    ...     distribution_list=None,
    ...     bu_indicator='merchav',
    ...     mail_subject=None,
    ...     mail_body=None
    ... )
    >>> config_merchav.requires_bu_parameter()
    True
    """
    report_id: int
    report_name: str
    sql_query: str
    interval: str  # NVARCHAR2: bi-daily, daily, weekly, monthly, quarterly, yearly, yesterday
    distribution_list: Optional[str]
    bu_indicator: str  # NVARCHAR2: mador, branches, merchav, compliance
    mail_subject: Optional[str]
    mail_body: Optional[str]

    def get_distribution_list_emails(self) -> List[str]:
        """Parse comma-separated distribution list into email list"""
        if not self.distribution_list:
            return []
        return [email.strip() for email in self.distribution_list.split(',') if email.strip()]

    def requires_bu_parameter(self) -> bool:
        """Check if query requires :bu parameter (branches/merchav)"""
        name = (self.bu_indicator or '').strip().lower()
        return name in ('branches', 'merchav')


