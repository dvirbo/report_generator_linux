"""
Report Configuration Model
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ReportConfig:
    """
    Report configuration model
    """
    report_id: int
    report_name: str
    sql_query: str
    interval: str  # NVARCHAR2: bi-daily, daily, weekly, monthly, quarterly, yearly, yesterday
    distribution_list: Optional[str]
    bu_indicator: str  # NVARCHAR2: mador, branches, merchav, compliance
    mail_subject: Optional[str]
    mail_body: Optional[str]
    send_on_no_data: bool = False  # Whether to send email even when query returns no data

    def get_distribution_list_emails(self) -> List[str]:
        """Parse comma-separated distribution list into email list"""
        if not self.distribution_list:
            return []
        return [email.strip() for email in self.distribution_list.split(',') if email.strip()]

    def requires_bu_parameter(self) -> bool:
        """Check if query requires :bu parameter (branches/merchav)"""
        name = (self.bu_indicator or '').strip().lower()
        return name in ('branches', 'merchav')


