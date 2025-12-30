"""
Report Generator
Main orchestration engine for report generation and distribution
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from collections import defaultdict

from .models.report_config import ReportConfig
from .models.recipient import Recipient
from .services.database_service import DatabaseService
from .services.query_executor import QueryExecutor
from .services.recipient_service import RecipientService
from .services.email_service import EmailService
from .services.csv_generator import CSVGenerator
from .services.logger_service import LoggerService
from .utils.date_calculator import DateCalculator

logger = logging.getLogger(__name__)

EMAIL_SEND_FAILED_MESSAGE = 'Email send failed'


class ProcessingMode(Enum):
    SINGLE_QUERY_BULK_EMAIL = "single_query_bulk_email"
    PER_RECIPIENT_QUERY_EMAIL = "per_recipient_query_email"


@dataclass
class ReportProcessingConfig:
    bu_indicator: str
    recipient_source: str  # 'distribution_list' or 'database'
    requires_bu_parameter: bool
    processing_mode: ProcessingMode


class ReportGenerator:

    def __init__(
        self,
        db_service: DatabaseService,
        query_executor: QueryExecutor,
        recipient_service: RecipientService,
        email_service: EmailService,
        csv_generator: CSVGenerator,
        logger_service: LoggerService,
        date_calculator: DateCalculator
    ):
        self.db_service = db_service
        self.query_executor = query_executor
        self.recipient_service = recipient_service
        self.email_service = email_service
        self.csv_generator = csv_generator
        self.logger_service = logger_service
        self.date_calculator = date_calculator

    def process_all_reports(self, interval_name: Optional[str] = None, base_datetime: Optional[datetime] = None) -> Dict[str, Any]:
        logger.info("Starting report generation process")

        if interval_name is not None and base_datetime is None:
            raise ValueError("base_datetime is required when interval_name is provided")

        active_reports = self._load_active_reports(interval_name)
        logger.info(f"Found {len(active_reports)} active reports")

        summary = {'total_reports': len(active_reports), 'successful': 0, 'failed': 0, 'results': []}

        for report in active_reports:
            try:
                result = self.process_single_report(report.report_id, preloaded_report=report, base_datetime=base_datetime)
                summary['results'].append(result)
                if result['status'] == 'SUCCESS':
                    summary['successful'] += 1
                else:
                    summary['failed'] += 1
            except Exception as e:
                logger.error(f"Failed to process report {report.report_id}: {e}")
                summary['failed'] += 1
                summary['results'].append({'report_id': report.report_id, 'report_name': report.report_name, 'status': 'FAILED', 'error': str(e)})

        logger.info(f"Report generation completed: {summary['successful']} successful, {summary['failed']} failed")
        return summary

    def process_single_report(
        self,
        report_id: int,
        preloaded_report: Optional[ReportConfig] = None,
        base_datetime: Optional[datetime] = None
    ) -> Dict[str, Any]:
        execution_id = None
        try:
            report = preloaded_report or self._load_report(report_id)
            if not report:
                raise ValueError(f"Report {report_id} not found")
            if preloaded_report and preloaded_report.report_id != report_id:
                raise ValueError(f"Preloaded report ID {preloaded_report.report_id} does not match requested ID {report_id}")

            execution_id = self.logger_service.log_execution_start(report_id)
            if base_datetime is None:
                logger.info("No base datetime provided, using current datetime")
                base_datetime = datetime.now()
            start_dt, end_dt = self.date_calculator.calculate_date_range_by_name(report.interval, base_datetime)

            logger.info(f"Processing report {report_id} ({report.report_name}) for period {start_dt} to {end_dt}")

            result = self._handle_report(report, start_dt, end_dt, execution_id)

            self.logger_service.log_execution_end(execution_id, 'SUCCESS', {
                'records_returned': result.get('records_returned', 0),
                'recipients_count': result.get('recipients_count', 0),
                'query_params': {'start_date': str(start_dt), 'end_date': str(end_dt)}
            })

            result['status'] = 'SUCCESS'
            return result

        except Exception as e:
            logger.error(f"Report {report_id} failed: {e}")
            if execution_id:
                self.logger_service.log_error(execution_id, e)
                self.logger_service.log_execution_end(execution_id, 'FAILED', {
                    'error_message': str(e),
                    'error_stack': str(e)
                })
            return {'report_id': report_id, 'status': 'FAILED', 'error': str(e)}

    def _load_active_reports(self, interval_name: Optional[str] = None) -> List[ReportConfig]:
        query = """
            SELECT report_id, report_name, sql_query, interval_desc, distribution_list,
                   bu_indicator, mail_subject, mail_body
            FROM report_config
            WHERE active_indicator = 1
        """
        params: Dict[str, Any] = {}
        if interval_name is not None:
            query += " AND LOWER(interval_desc) = :interval_desc"
            params['interval_desc'] = (interval_name or '').lower()
        query += " ORDER BY report_id"
        rows = self.db_service.execute_query(query, params)
        reports: List[ReportConfig] = []
        for row in rows:
            # Handle both uppercase and lowercase column names from Oracle
            report_id = row.get('REPORT_ID') or row.get('report_id')
            if report_id is None:
                logger.error(f"Missing report_id in row: {row}")
                continue
            # Ensure report_id is an integer, not a list
            if isinstance(report_id, list):
                if len(report_id) > 0:
                    report_id = report_id[0]
                else:
                    logger.error(f"report_id is an empty list in row: {row}")
                    continue
            
            reports.append(ReportConfig(
                report_id=int(report_id),
                report_name=row.get('REPORT_NAME') or row.get('report_name') or '',
                sql_query=row.get('SQL_QUERY') or row.get('sql_query') or '',
                interval=row.get('INTERVAL_DESC') or row.get('interval_desc') or '',
                distribution_list=row.get('DISTRIBUTION_LIST') or row.get('distribution_list'),
                bu_indicator=row.get('BU_INDICATOR') or row.get('bu_indicator') or '',
                mail_subject=row.get('MAIL_SUBJECT') or row.get('mail_subject'),
                mail_body=row.get('MAIL_BODY') or row.get('mail_body'),
            ))
        return reports

    def _load_report(self, report_id: int) -> Optional[ReportConfig]:
        query = """
            SELECT report_id, report_name, sql_query, interval_DESC, distribution_list,
                   bu_indicator, mail_subject, mail_body, active_indicator
            FROM report_config
            WHERE report_id = :report_id
        """
        rows = self.db_service.execute_query(query, {'report_id': report_id})
        if not rows:
            return None
        row = rows[0]
        # Handle both uppercase and lowercase column names from Oracle
        report_id_val = row.get('REPORT_ID') or row.get('report_id')
        if isinstance(report_id_val, list) and len(report_id_val) > 0:
            report_id_val = report_id_val[0]
        
        return ReportConfig(
            report_id=int(report_id_val) if report_id_val is not None else report_id,
            report_name=row.get('REPORT_NAME') or row.get('report_name') or '',
            sql_query=row.get('SQL_QUERY') or row.get('sql_query') or '',
            interval=row.get('INTERVAL_DESC') or row.get('interval_DESC') or row.get('interval_desc') or '',
            distribution_list=row.get('DISTRIBUTION_LIST') or row.get('distribution_list'),
            bu_indicator=row.get('BU_INDICATOR') or row.get('bu_indicator') or '',
            mail_subject=row.get('MAIL_SUBJECT') or row.get('mail_subject'),
            mail_body=row.get('MAIL_BODY') or row.get('mail_body')
            )

    def _get_processing_config(self, bu_indicator: str) -> ReportProcessingConfig:
        """
        Get processing configuration for a BU indicator.
        
        >>> from unittest.mock import Mock
        >>> mock_db = Mock()
        >>> mock_query_executor = Mock()
        >>> mock_recipient_service = Mock()
        >>> mock_email_service = Mock()
        >>> mock_csv_generator = Mock()
        >>> mock_logger_service = Mock()
        >>> from src.utils.date_calculator import DateCalculator
        >>> 
        >>> generator = ReportGenerator(
        ...     mock_db, mock_query_executor, mock_recipient_service,
        ...     mock_email_service, mock_csv_generator, mock_logger_service,
        ...     DateCalculator()
        ... )
        >>> 
        >>> # Test mador configuration
        >>> config = generator._get_processing_config('mador')
        >>> config.bu_indicator == 'mador'
        True
        >>> config.recipient_source == 'distribution_list'
        True
        >>> config.processing_mode == ProcessingMode.SINGLE_QUERY_BULK_EMAIL
        True
        >>> 
        >>> # Test branches configuration
        >>> config = generator._get_processing_config('branches')
        >>> config.recipient_source == 'database'
        True
        >>> config.requires_bu_parameter == True
        True
        >>> config.processing_mode == ProcessingMode.PER_RECIPIENT_QUERY_EMAIL
        True
        >>> 
        >>> # Test invalid BU indicator
        >>> try:
        ...     generator._get_processing_config('invalid')
        ... except ValueError as e:
        ...     'Invalid BU indicator' in str(e)
        True
        """
        name = (bu_indicator or '').strip().lower()
        mapping = {
            'mador': ReportProcessingConfig(
                bu_indicator='mador',
                recipient_source='distribution_list',
                requires_bu_parameter=False,
                processing_mode=ProcessingMode.SINGLE_QUERY_BULK_EMAIL
            ),
            'branches': ReportProcessingConfig(
                bu_indicator='branches',
                recipient_source='database',
                requires_bu_parameter=True,
                processing_mode=ProcessingMode.PER_RECIPIENT_QUERY_EMAIL
            ),
            'merchav': ReportProcessingConfig(
                bu_indicator='merchav',
                recipient_source='database',
                requires_bu_parameter=True,
                processing_mode=ProcessingMode.PER_RECIPIENT_QUERY_EMAIL
            ),
            'compliance': ReportProcessingConfig(
                bu_indicator='compliance',
                recipient_source='database',
                requires_bu_parameter=False,
                processing_mode=ProcessingMode.SINGLE_QUERY_BULK_EMAIL )
        }
        if name not in mapping:
            raise ValueError(f"Invalid BU indicator: {bu_indicator}")
        return mapping[name]

    def _get_recipients(self, report: ReportConfig, config: ReportProcessingConfig) -> List[Recipient]:
        if config.recipient_source == 'distribution_list':
            return [Recipient(email=e) for e in report.get_distribution_list_emails()]
        if config.recipient_source == 'database':
            return self.recipient_service.get_recipients(config.bu_indicator)
        raise ValueError(f"Invalid recipient source: {config.recipient_source}")

    def _handle_report(self, report: ReportConfig, start_dt: datetime, end_dt: datetime, execution_id: int) -> Dict[str, Any]:
        '''
        Handle report processing based on the processing mode and the report configuration
        
        Args:
            report: ReportConfig object containing the report configuration
            start_dt: Start datetime for the report period
            end_dt: End datetime for the report period
            execution_id: Execution ID from logger service
        
        Returns:
            Dictionary containing report ID, name, recipients count, and records returned
        
        Raises:
            ValueError: If unsupported processing mode or no recipients found
        '''
        config = self._get_processing_config(report.bu_indicator)
        recipients = self._get_recipients(report, config)
        if not recipients:
            logger.warning(f"No recipients found for report {report.report_id}")
            return {'report_id': report.report_id, 'report_name': report.report_name, 'recipients_count': 0, 'records_returned': 0}

        if config.processing_mode == ProcessingMode.SINGLE_QUERY_BULK_EMAIL: #mador and compliance reports are processed using this mode
            return self._process_single_query_bulk_email(report, start_dt, end_dt, execution_id, recipients, config)
        if config.processing_mode == ProcessingMode.PER_RECIPIENT_QUERY_EMAIL: #branches and merchav reports are processed using this mode
            return self._process_per_bu_group_query_email(report, start_dt, end_dt, execution_id, recipients, config)
        raise ValueError(f"Unsupported processing mode: {config.processing_mode}")

    def _process_single_query_bulk_email(
        self,
        report: ReportConfig,
        start_dt: datetime,
        end_dt: datetime,
        execution_id: int,
        recipients: List[Recipient],
        config: ReportProcessingConfig
    ) -> Dict[str, Any]:
        '''
        Process single query bulk email. 
        the method will execute the query and get the results and send the email to the recipients.
        
        Args:
            report: ReportConfig object containing the report configuration
            start_dt: Start datetime for the report period
            end_dt: End datetime for the report period
            execution_id: Execution ID from logger service
            recipients: List of recipients
            config: ReportProcessingConfig containing the processing configuration
        
        Returns:
            Dictionary containing report ID, name, recipients count, and records returned
        
        Raises:
            ValueError: If unsupported processing mode or no recipients found
        '''
        # Execute the query and get the results
        params = {'start_date': start_dt, 'end_date': end_dt}
        results = self.query_executor.execute_query(report.sql_query, params, requires_bu=config.requires_bu_parameter)
        has_data = len(results) > 0

        # If no data, log and skip email sending
        if not has_data:
            logger.info(f"No data returned for report {report.report_id}, skipping email sending")
            for r in recipients:
                self.logger_service.log_email_delivery(
                    execution_id, 
                    report.report_id, 
                    r.email, 
                    r.full_name, 
                    r.bu_internal_id, 
                    'NO_DATA',
                    error_message='No data available for the selected period'
                )
            return {'report_id': report.report_id, 'report_name': report.report_name, 'recipients_count': 0, 'records_returned': 0}

        # Generate CSV and send email only when there is data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filepath = self.csv_generator.generate_csv(results, report.report_name, timestamp)
        
        recipient_emails = [r.email for r in recipients]
        success = self.email_service.send_report_email_to_list(recipient_emails, report, csv_filepath, has_data)

        for r in recipients:
            status = 'SENT' if success else 'FAILED'
            self.logger_service.log_email_delivery(execution_id, report.report_id, r.email, r.full_name, r.bu_internal_id, status)

        if csv_filepath:
            self.csv_generator.cleanup_file(csv_filepath)

        return {'report_id': report.report_id, 'report_name': report.report_name, 'recipients_count': len(recipients) if success else 0, 'records_returned': len(results)}

    def _process_per_bu_group_query_email(
        self,
        report: ReportConfig,
        start_dt: datetime,
        end_dt: datetime,
        execution_id: int,
        recipients: List[Recipient],
        config: ReportProcessingConfig
    ) -> Dict[str, Any]:
        """
        Process report by grouping recipients by bu_identifier and sending one email per group.
        Each group shares the same CSV file generated from a single query execution.
        
        Args:
            report: ReportConfig object containing the report configuration
            start_dt: Start datetime for the report period
            end_dt: End datetime for the report period
            execution_id: Execution ID from logger service
            recipients: List of recipients
            config: ReportProcessingConfig containing the processing configuration
        
        Returns:
            Dictionary containing report ID, name, recipients count, and records returned
        """
        success_count = 0
        total_records = 0

        # Group recipients by bu_identifier
        recipients_by_bu = defaultdict(list)
        for recipient in recipients:
            bu_id = recipient.bu_identifier
            if bu_id:
                recipients_by_bu[bu_id].append(recipient)
            else:
                logger.warning(f"Recipient {recipient.email} has no bu_identifier, skipping")

        logger.info(f"Grouped {len(recipients)} recipients into {len(recipients_by_bu)} BU groups")
        
        # Process each BU group
        for bu_identifier, group_recipients in recipients_by_bu.items():
            try:
                # Execute query once per BU group
                params = {'start_date': start_dt, 'end_date': end_dt}
                if config.requires_bu_parameter:
                    params['bu'] = bu_identifier

                results = self.query_executor.execute_query(report.sql_query, params, requires_bu=config.requires_bu_parameter)
                has_data = len(results) > 0
                total_records += len(results)

                # If no data, log and skip email sending for this BU group
                if not has_data:
                    logger.info(f"No data returned for report {report.report_id}, BU {bu_identifier}, skipping email sending")
                    for recipient in group_recipients:
                        self.logger_service.log_email_delivery(
                            execution_id, 
                            report.report_id, 
                            recipient.email, 
                            recipient.full_name, 
                            recipient.bu_internal_id, 
                            'NO_DATA',
                            error_message='No data available for the selected period'
                        )
                    continue

                # Generate CSV once per BU group (only when there is data)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filepath = self.csv_generator.generate_csv(results, report.report_name, timestamp)

                # Send one email to all recipients in the group
                recipient_emails = [r.email for r in group_recipients]
                success = self.email_service.send_report_email_to_list(recipient_emails, report, csv_filepath, has_data)
                
                # Log email delivery for all recipients in the group
                status = 'SENT' if success else 'FAILED'
                error_message = None if success else EMAIL_SEND_FAILED_MESSAGE
                for recipient in group_recipients:
                    if success:
                        success_count += 1
                    self.logger_service.log_email_delivery(
                        execution_id, 
                        report.report_id, 
                        recipient.email, 
                        recipient.full_name, 
                        recipient.bu_internal_id, 
                        status,
                        error_message=error_message
                    )

                # Cleanup CSV file
                if csv_filepath:
                    self.csv_generator.cleanup_file(csv_filepath)

            except Exception as e:
                logger.error(f"Failed to process BU group {bu_identifier}: {e}")
                # Log failure for all recipients in the group
                for recipient in group_recipients:
                    self.logger_service.log_email_delivery(
                        execution_id, 
                        report.report_id, 
                        recipient.email, 
                        recipient.full_name, 
                        recipient.bu_internal_id, 
                        'FAILED', 
                        error_message=str(e)
                    )

        return {'report_id': report.report_id, 'report_name': report.report_name, 'recipients_count': success_count, 'records_returned': total_records}



