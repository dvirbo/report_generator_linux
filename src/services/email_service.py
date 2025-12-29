"""
Email Service
Send email reports with CSV attachments
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional
from ..models.recipient import Recipient
from ..models.report_config import ReportConfig

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending email reports
    
    Note: Email sending functionality requires manual verification in development environment.
    These doctests verify email construction and validation without actually sending emails.
    
    >>> # Test email validation
    >>> EmailService.validate_email_address('test@example.com')
    True
    >>> EmailService.validate_email_address('invalid.email')
    False
    >>> EmailService.validate_email_address('user@domain.co.uk')
    True
    >>> 
    >>> # Test distribution list parsing
    >>> emails = EmailService.parse_distribution_list('user1@example.com, user2@example.com, user3@example.com')
    >>> len(emails)
    3
    >>> 'user1@example.com' in emails
    True
    >>> 'user2@example.com' in emails
    True
    >>> 
    >>> # Test empty distribution list
    >>> EmailService.parse_distribution_list('')
    []
    >>> EmailService.parse_distribution_list(None)
    []
    >>> 
    >>> # Test email service initialization (without sending)
    >>> config = {
    ...     'smtp_server': 'smtp.example.com',
    ...     'smtp_port': 587,
    ...     'smtp_use_tls': True,
    ...     'smtp_username': 'user@example.com',
    ...     'smtp_password': 'password',
    ...     'from_email': 'sender@example.com',
    ...     'from_name': 'Test Sender'
    ... }
    >>> email_service = EmailService(config)
    >>> email_service.smtp_server == 'smtp.example.com'
    True
    >>> email_service.from_email == 'sender@example.com'
    True
    >>> 
    >>> # Test email content building (placeholder - verify manually)
    >>> # Use a simple mock object to avoid import issues in doctest
    >>> class MockReport:
    ...     def __init__(self):
    ...         self.mail_body = 'This is a test email body.'
    ...         self.mail_subject = 'Test Subject'
    >>> mock_report = MockReport()
    >>> body = email_service._build_email_content(mock_report, has_data=True)
    >>> 'This is a test email body.' in body
    True
    >>> 'Please find the report data attached' in body
    True
    >>> 
    >>> # Test email content for no data case
    >>> body_no_data = email_service._build_email_content(mock_report, has_data=False)
    >>> 'No data available' in body_no_data
    True
    """

    def __init__(self, config: dict):
        """
        Initialize email service
        
        Args:
            config: Email configuration dictionary
        """
        self.config = config
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_use_tls = config.get('smtp_use_tls', True)
        self.smtp_username = config.get('smtp_username')
        self.smtp_password = config.get('smtp_password')
        self.from_email = config.get('from_email')
        self.from_name = config.get('from_name', 'Automated Report System')

    def send_report_email(
        self,
        recipient: Recipient,
        report: ReportConfig,
        csv_filepath: Optional[str] = None,
        has_data: bool = True
    ) -> bool:
        """
        Send report email to recipient
        
        Args:
            recipient: Recipient object
            report: ReportConfig object
            csv_filepath: Path to CSV file attachment (optional)
            has_data: Whether query returned data
        
        Returns:
            True if email sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient.email
            msg['Subject'] = report.mail_subject
            
            # Build email body
            body = self._build_email_content(report, has_data)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Attach CSV file if provided and has data
            if csv_filepath and has_data:
                self._attach_csv_file(msg, csv_filepath)
            
            # Send email
            self._send_email(msg, [recipient.email])
            
            logger.info(f"Email sent successfully to {recipient.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient.email}: {e}")
            return False

    def send_report_email_to_list(
        self,
        recipients: List[str],
        report: ReportConfig,
        csv_filepath: Optional[str] = None,
        has_data: bool = True
    ) -> bool:
        """
        Send report email to multiple recipients
        
        Args:
            recipients: List of email addresses
            report: ReportConfig object
            csv_filepath: Path to CSV file attachment (optional)
            has_data: Whether query returned data
        
        Returns:
            True if all emails sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = report.mail_subject
            
            # Build email body
            body = self._build_email_content(report, has_data)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Attach CSV file if provided and has data
            if csv_filepath and has_data:
                self._attach_csv_file(msg, csv_filepath)
            
            # Send email
            self._send_email(msg, recipients)
            
            logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to recipients: {e}")
            return False

    def _build_email_content(self, report: ReportConfig, has_data: bool) -> str:
        """
        Build email body content
        
        Args:
            report: ReportConfig object
            has_data: Whether query returned data
        
        Returns:
            Email body text
        """
        from datetime import datetime
        
        body_parts = []
        
        if report.mail_body:
            body_parts.append(report.mail_body)
            body_parts.append("")
        
        if not has_data:
            body_parts.append("No data available for the selected period.")
        else:
            body_parts.append("Please find the report data attached as a CSV file.")
        
        body_parts.append("")
        body_parts.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(body_parts)

    def _attach_csv_file(self, msg: MIMEMultipart, csv_filepath: str):
        """
        Attach CSV file to email message
        
        Args:
            msg: MIMEMultipart message object
            csv_filepath: Path to CSV file
        """
        try:
            file_path = Path(csv_filepath)
            if not file_path.exists():
                logger.warning(f"CSV file not found: {csv_filepath}")
                return
            
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {file_path.name}'
            )
            msg.attach(part)
            
            logger.debug(f"Attached CSV file: {csv_filepath}")
            
        except Exception as e:
            logger.error(f"Failed to attach CSV file: {e}")
            raise

    def _send_email(self, msg: MIMEMultipart, recipients: List[str]):
        """
        Send email via SMTP
        
        Args:
            msg: MIMEMultipart message object
            recipients: List of recipient email addresses
        """
        try:
            # Create SMTP connection with timeout (default 30 seconds)
            timeout = self.config.get('smtp_timeout', 30)
            server = smtplib.SMTP(timeout=timeout)
            server.connect(self.smtp_server, self.smtp_port)
            
            if self.smtp_use_tls:
                server.starttls()
            
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            
            server.send_message(msg, to_addrs=recipients)
            server.quit()
                
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            raise

    @staticmethod
    def validate_email_address(email: str) -> bool:
        """
        Validate email address format
        
        Args:
            email: Email address string
        
        Returns:
            True if valid
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def parse_distribution_list(distribution_list: str) -> List[str]:
        """
        Parse comma-separated distribution list
        
        Args:
            distribution_list: Comma-separated email addresses
        
        Returns:
            List of email addresses
        """
        if not distribution_list:
            return []
        
        emails = [email.strip() for email in distribution_list.split(',') if email.strip()]
        # Validate emails
        valid_emails = [email for email in emails if EmailService.validate_email_address(email)]
        return valid_emails

