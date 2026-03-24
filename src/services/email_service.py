"""
Email Service
Send email reports with CSV attachments
"""

import smtplib
import logging
import csv
import html
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional, Tuple
from ..models.recipient import Recipient
from ..models.report_config import ReportConfig

logger = logging.getLogger(__name__)

# Module-level variable to store current report date (set before email sending)
_current_report_date: Optional[datetime] = None


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
        self.attach_csv = config.get('attach_csv', True)
    
    @staticmethod
    def set_report_date(report_date: Optional[datetime]):
        """
        Set the current report date for email body display.
        This should be called before sending emails for a report.
        
        Args:
            report_date: Date parameter used for the report (optional)
        """
        global _current_report_date
        _current_report_date = report_date
    
    @staticmethod
    def _get_report_title_with_date(report_name: str) -> str:
        """
        Get report title with date appended if available.
        
        Args:
            report_name: Report name
            
        Returns:
            Report name with date (e.g., "Report Name - 01/01/2026")
        """
        global _current_report_date
        if _current_report_date:
            report_date_str = _current_report_date.strftime('%d/%m/%Y')
            return f"{report_name} - {report_date_str}"
        return report_name

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
            # Create message (outer mixed, inner alternative for plain+HTML)
            msg = MIMEMultipart('mixed')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient.email
            # Set subject - use report subject or generate one with date
            global _current_report_date
            if report.mail_subject:
                subject = report.mail_subject
                # Append date to custom subject if date is available
                if _current_report_date:
                    report_date_str = _current_report_date.strftime('%d/%m/%Y')
                    subject = f"{subject} - {report_date_str}"
            else:
                subject = f"Report: {EmailService._get_report_title_with_date(report.report_name)}"
            msg['Subject'] = subject
            
            # Build multipart/alternative body (plain + HTML).
            alt = self._build_alternative_body(report=report, has_data=has_data, csv_filepath=csv_filepath)
            msg.attach(alt)
            
            # Attach CSV file optionally (HTML body always includes a table when CSV exists)
            if self.attach_csv and csv_filepath and has_data:
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
            # Create message (outer mixed, inner alternative for plain+HTML)
            msg = MIMEMultipart('mixed')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = ', '.join(recipients)
            # Set subject - use report subject or generate one with date
            global _current_report_date
            if report.mail_subject:
                subject = report.mail_subject
                # Append date to custom subject if date is available
                if _current_report_date:
                    report_date_str = _current_report_date.strftime('%d/%m/%Y')
                    subject = f"{subject} - {report_date_str}"
            else:
                subject = f"Report: {EmailService._get_report_title_with_date(report.report_name)}"
            msg['Subject'] = subject
            
            # Build multipart/alternative body (plain + HTML).
            alt = self._build_alternative_body(report=report, has_data=has_data, csv_filepath=csv_filepath)
            msg.attach(alt)
            
            # Attach CSV file optionally (HTML body always includes a table when CSV exists)
            if self.attach_csv and csv_filepath and has_data:
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
        Build legacy plain-text email content.

        Note: New pipeline uses multipart/alternative with both plain-text and HTML bodies.
        
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

    def _build_alternative_body(
        self,
        report: ReportConfig,
        has_data: bool,
        csv_filepath: Optional[str],
    ) -> MIMEMultipart:
        """
        Build multipart/alternative email body:
        - Plain-text fallback part
        - HTML part (mandatory). If CSV exists, HTML includes a table rendering of the CSV.
        """
        alt = MIMEMultipart('alternative')

        plain = self._build_plain_text_body(report=report, has_data=has_data, csv_filepath=csv_filepath)
        html_body = self._build_html_body(report=report, has_data=has_data, csv_filepath=csv_filepath)

        alt.attach(MIMEText(plain, 'plain', 'utf-8'))
        alt.attach(MIMEText(html_body, 'html', 'utf-8'))
        return alt

    def _build_plain_text_body(self, report: ReportConfig, has_data: bool, csv_filepath: Optional[str]) -> str:
        """
        Plain-text fallback body. If a CSV exists, includes the raw CSV text (no truncation).
        """
        base = self._build_email_content(report, has_data)
        
        # Prepend report name with date to the base content
        report_title_with_date = EmailService._get_report_title_with_date(report.report_name or "Report")
        base = f"Report: {report_title_with_date}\n\n{base}"
        
        if not (csv_filepath and has_data):
            return base

        csv_text = self._read_csv_as_text(csv_filepath)
        return (
            base
            + "\n\n"
            + "CSV data:\n"
            + csv_text
        )

    def _build_html_body(self, report: ReportConfig, has_data: bool, csv_filepath: Optional[str]) -> str:
        """
        HTML email body (mandatory). If a CSV exists, renders it as an HTML table with:
        - first row as <th> headers
        - remaining rows as <td>
        - all rows included (no truncation)
        - HTML-escaped cell contents
        """
        # Get report title with date on same line
        report_title = html.escape(EmailService._get_report_title_with_date(report.report_name or "Report"))
        intro_parts: List[str] = []

        if report.mail_body:
            # Preserve basic formatting of mail_body while still escaping HTML.
            intro_parts.append("<div>")
            intro_parts.append(html.escape(report.mail_body).replace("\n", "<br/>"))
            intro_parts.append("</div>")

        if not has_data:
            intro_parts.append("<p>הדוח אינו מכיל תוצאות עבור התקופה שנבחרה</p>")

        table_html = ""
        if csv_filepath and has_data:
            rows = self._read_csv_rows(csv_filepath)
            table_html = self._csv_rows_to_html_table(rows)

        return (
            "<!doctype html>"
            "<html dir=\"rtl\">"
            "<head>"
            "<meta charset=\"utf-8\"/>"
            "<style>"
            "table{{border-collapse:collapse;width:100%;}}"
            "th,td{{border:1px solid #ddd;padding:6px;vertical-align:top;}}"
            "th{{background:#f5f5f5;text-align:center;}}"
            "</style>"
            "</head>"
            "<body>"
            "<h3>{}</h3>"
            "{}"
            "{}"
            "</body>"
            "</html>"
        ).format(report_title, "".join(intro_parts), table_html)

    def _read_csv_as_text(self, csv_filepath: str) -> str:
        """
        Read the CSV as text using utf-8-sig to handle BOM.
        """
        file_path = Path(csv_filepath)
        if not file_path.exists():
            return "(CSV file not found)"
        with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
            return f.read()

    def _sniff_csv_delimiter(self, sample: str) -> str:
        """
        Attempt to detect delimiter using csv.Sniffer; fallback to comma.
        """
        try:
            dialect = csv.Sniffer().sniff(sample)
            return getattr(dialect, 'delimiter', ',') or ','
        except Exception:
            return ','

    def _read_csv_rows(self, csv_filepath: str) -> List[List[str]]:
        """
        Read CSV rows from disk (no truncation).
        - Detect delimiter when possible (csv.Sniffer), fallback to comma.
        - Read with utf-8-sig to handle BOM.
        """
        file_path = Path(csv_filepath)
        if not file_path.exists():
            logger.warning(f"CSV file not found for HTML rendering: {csv_filepath}")
            return []

        # Read a sample for delimiter detection.
        with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
            sample = f.read(32768)
            delimiter = self._sniff_csv_delimiter(sample)
            f.seek(0)
            reader = csv.reader(f, delimiter=delimiter)
            return [[cell if cell is not None else "" for cell in row] for row in reader]

    def _csv_rows_to_html_table(self, rows: List[List[str]]) -> str:
        """
        Convert CSV rows into an HTML <table>.
        First row is headers (<th>), remaining rows are data (<td>).
        Escapes all cell contents for safe HTML.
        """
        if not rows:
            return "<p><em>No CSV rows found.</em></p>"

        header = rows[0]
        data_rows = rows[1:] if len(rows) > 1 else []

        def th(cell: str) -> str:
            return "<th>{}</th>".format(html.escape(str(cell)))

        def td(cell: str) -> str:
            return "<td>{}</td>".format(html.escape(str(cell)))

        head_html = "<tr>{}</tr>".format("".join(th(c) for c in header))
        body_html = "".join("<tr>{}</tr>".format("".join(td(c) for c in row)) for row in data_rows)

        return "<table><thead>{}</thead><tbody>{}</tbody></table>".format(head_html, body_html)

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
            
            # Use text/csv MIME type (matching the working test script)
            # The key difference: use add_header with keyword arguments for proper RFC 2231 encoding
            # of non-ASCII characters (Hebrew) in the filename
            part = MIMEBase('text', 'csv')
            part.set_payload(file_data)
            encoders.encode_base64(part)
            
            # Set Content-Type with proper parameter encoding for non-ASCII filenames
            # Using keyword argument syntax tells Python to properly encode the filename
            if 'Content-Type' in part:
                del part['Content-Type']
            part.add_header('Content-Type', 'text/csv', charset='utf-8', name=filename)
            
            # Set Content-Disposition with proper RFC 2231 encoding for non-ASCII filenames
            # This is the KEY FIX: using keyword argument instead of string formatting
            # Python's email library will properly encode Hebrew characters
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            
            # Log the actual headers being set for debugging
            logger.debug(f"CSV attachment headers - Content-Type: {part.get('Content-Type')}, "
                        f"Content-Disposition: {part.get('Content-Disposition')}, filename: {filename}")
            
            # Additional check: verify the filename has .csv extension
            if not filename.lower().endswith('.csv'):
                logger.warning(f"WARNING: Filename does not end with .csv: {filename}")
            
            msg.attach(part)
            
            # Log final message structure for debugging
            logger.debug(f"Attached CSV file: {csv_filepath} with filename: {filename}")
            logger.debug(f"Final attachment Content-Type: {part.get('Content-Type')}")
            logger.debug(f"Final attachment Content-Disposition: {part.get('Content-Disposition')}")
            
            # Additional debugging: log all headers on the part
            logger.debug(f"All attachment headers: {dict(part.items())}")
            
            # Verify the filename has .csv extension - this is critical
            if not filename.lower().endswith('.csv'):
                logger.error(f"ERROR: Filename does not end with .csv: {filename}")
            
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
            
            # Log full message structure before sending for debugging
            logger.debug("=== Full message structure before sending ===")
            logger.debug(f"Message headers: {dict(msg.items())}")
            for i, payload_part in enumerate(msg.get_payload()):
                if isinstance(payload_part, MIMEBase):
                    logger.debug(f"Part {i}: Content-Type={payload_part.get('Content-Type')}, "
                              f"Content-Disposition={payload_part.get('Content-Disposition')}")
                elif hasattr(payload_part, 'get_content_type'):
                    logger.debug(f"Part {i}: Content-Type={payload_part.get_content_type()}")
            logger.debug("=== End message structure ===")
            
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


