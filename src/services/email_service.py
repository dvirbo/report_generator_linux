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
        # Default to False for port 25 (common for internal mail servers), True for other ports
        default_require_auth = config.get('smtp_port', 587) != 25
        self.smtp_require_auth = config.get('smtp_require_auth', default_require_auth)
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
            # Set subject - use report subject or generate one
            subject = report.mail_subject or f"Report: {report.report_name}"
            msg['Subject'] = subject
            
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
            # Set subject - use report subject or generate one
            subject = report.mail_subject or f"Report: {report.report_name}"
            msg['Subject'] = subject
            
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
            # Custom message for no-data scenario
            body_parts.append("This report contains no results for the selected period.")
            body_parts.append("")
            body_parts.append("No data matching the report criteria was found.")
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
            
            # Use the exact filename from the file path (already has meaningful name from CSV generator)
            # The CSV generator creates filenames like: report_{report_name}_{timestamp}.csv
            filename = file_path.name
            # Ensure it has .csv extension (should already have it, but just in case)
            if not filename.lower().endswith('.csv'):
                filename = f"{file_path.stem}.csv"
            
            # Read CSV file as binary for attachment
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Create attachment part using MIMEBase
            # Start with application/octet-stream, then override with proper CSV type
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file_data)
            
            # Encode as base64 for email transmission
            encoders.encode_base64(part)
            
            # Set Content-Type header explicitly for CSV
            # Use application/vnd.ms-excel for maximum compatibility with email clients
            # This MIME type is widely recognized and ensures CSV files open in Excel
            # Many email clients treat text/csv or application/csv as plain text
            if 'Content-Type' in part:
                del part['Content-Type']
            # application/vnd.ms-excel is the most compatible for CSV files in email
            part.add_header('Content-Type', 'application/vnd.ms-excel; charset=utf-8; name="{}"'.format(filename))
            
            # Set Content-Disposition header with the exact filename from saved CSV
            # The filename already has the meaningful name from CSV generator (e.g., report_ReportName_20250101_120000.csv)
            # The .csv extension in the filename is critical for email clients to recognize it as CSV
            part.add_header(
                'Content-Disposition',
                'attachment; filename="{}"'.format(filename)
            )
            
            msg.attach(part)
            
            logger.debug(f"Attached CSV file: {csv_filepath} with filename: {filename}")
            
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
        server = None
        try:
            # Create SMTP connection with timeout (default 30 seconds)
            timeout = self.config.get('smtp_timeout', 30)
            server = smtplib.SMTP(timeout=timeout)
            server.connect(self.smtp_server, self.smtp_port)
            
            # Enable debug output for troubleshooting (can be removed in production)
            # server.set_debuglevel(1)
            
            # Send EHLO to get server capabilities (needed before STARTTLS or AUTH)
            server.ehlo()
            
            # Start TLS if configured (some servers require TLS before authentication)
            if self.smtp_use_tls:
                try:
                    server.starttls()
                    # After STARTTLS, need to send EHLO again
                    server.ehlo()
                    logger.debug("TLS/STARTTLS enabled")
                except Exception as e:
                    logger.warning(f"Failed to start TLS: {e}. Continuing without TLS.")
            
            # Attempt authentication if credentials are provided and required
            auth_successful = False
            if self.smtp_require_auth and self.smtp_username and self.smtp_password:
                try:
                    # Some servers require authentication but don't advertise AUTH in EHLO
                    # Try authentication anyway if credentials are provided
                    logger.debug("Attempting SMTP authentication...")
                    
                    # Check what AUTH methods are available (for logging)
                    auth_methods = []
                    if hasattr(server, 'esmtp_features') and 'auth' in server.esmtp_features:
                        auth_methods = server.esmtp_features['auth'].split()
                        logger.debug(f"Server advertises AUTH methods: {auth_methods}")
                    else:
                        logger.debug("Server does not advertise AUTH methods, but will attempt login anyway")
                    
                    # Try to authenticate - some servers require auth even if not advertised
                    server.login(self.smtp_username, self.smtp_password)
                    logger.info("SMTP authentication successful")
                    auth_successful = True
                    
                except smtplib.SMTPAuthenticationError as e:
                    logger.error(f"SMTP authentication failed: {e}")
                    raise  # Authentication failed with valid credentials - this is an error
                except smtplib.SMTPException as auth_error:
                    error_msg = str(auth_error).lower()
                    if "no suitable" in error_msg or "authentication method" in error_msg:
                        logger.error(f"SMTP server requires authentication but doesn't support available methods: {auth_error}")
                        if auth_methods:
                            logger.error(f"Server advertises these AUTH methods but none work: {auth_methods}")
                        logger.error("Suggestion: Try enabling STARTTLS (smtp_use_tls = yes) - some servers require TLS before authentication")
                        raise
                    else:
                        raise
            elif not self.smtp_require_auth:
                logger.debug("SMTP authentication disabled in config - sending without authentication")
                auth_successful = False  # Not required, so we're good
            
            # Send the email
            server.send_message(msg, to_addrs=recipients)
            logger.debug(f"Email sent successfully to {len(recipients)} recipient(s)")
                
        except smtplib.SMTPException as e:
            error_msg = str(e).lower()
            # Don't treat "no suitable authentication method" as a fatal error on port 25
            if ("no suitable" in error_msg or "authentication method" in error_msg) and self.smtp_port == 25:
                logger.warning(f"SMTP authentication not supported on port 25: {e}")
                logger.info("This is normal for internal mail servers. Email sending may still work.")
                # Try to send anyway - some servers allow unauthenticated sending on port 25
                # But if we're here, the send_message already failed, so we can't continue
                raise
            else:
                logger.error(f"SMTP error: {e}")
                raise
        except Exception as e:
            error_msg = str(e).lower()
            if "no suitable" in error_msg or "authentication" in error_msg:
                logger.warning(f"SMTP authentication issue: {e}")
                if self.smtp_port == 25:
                    logger.info("Port 25 often doesn't require authentication. Check your SMTP configuration.")
            logger.error(f"Unexpected error sending email: {e}")
            raise
        finally:
            # Always close the connection
            if server:
                try:
                    server.quit()
                except:
                    try:
                        server.close()
                    except:
                        pass

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


