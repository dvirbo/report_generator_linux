"""
Report Generator System - Main Entry Point
Usage:
    python main.py <interval> <yyyy-mm-dd>
    interval: bi-daily | daily | weekly | monthly | quarterly | yearly | yesterday
"""

import sys
import logging
import logging.handlers
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_loader import ConfigLoader
from src.utils.date_calculator import DateCalculator, validate_interval_name
from src.services.database_service import DatabaseService
from src.services.query_executor import QueryExecutor
from src.services.recipient_service import RecipientService
from src.services.email_service import EmailService
from src.services.csv_generator import CSVGenerator
from src.services.logger_service import LoggerService
from src.report_generator import ReportGenerator



def setup_logging(config: ConfigLoader, interval_name: str, base_datetime: datetime):
    logging_config = config.get_logging_config()
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, logging_config['level']))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if logging_config.get('log_to_console', True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if logging_config.get('log_to_file', True):
        # Create per-run log file: report_generator_<interval>_<YYYYMMDD>.log
        interval_slug = (interval_name or 'unknown').strip().lower().replace(' ', '-')
        date_slug = base_datetime.strftime("%Y%m%d")
        base_path = Path(logging_config['file_path'])
        log_dir = base_path.parent if base_path.suffix else base_path
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"report_generator_{interval_slug}_{date_slug}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=logging_config['file_size_mb'] * 1024 * 1024,
            backupCount=logging_config['backup_count']
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Report Generator System - Process reports based on interval',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py daily 2025-01-01  (yyyy-mm-dd format)
  python3 main.py last_bd 2025-01-01

Valid intervals: bi-daily, daily, weekly, monthly, quarterly, yearly, yesterday, last_bd
        """
    )
    parser.add_argument('interval', help='Interval name (bi-daily, daily, weekly, monthly, quarterly, yearly, yesterday)')
    parser.add_argument('date', help='Base date in yyyy-mm-dd format (interpreted per interval semantics)')
    return parser.parse_args()


def main():
    try:
        args = parse_arguments()

        if not validate_interval_name(args.interval):
            print(f"Error: Invalid interval name '{args.interval}'")
            print("Valid: bi-daily, daily, weekly, monthly, quarterly, yearly, last_bd")
            sys.exit(1)

        try:
            base_datetime = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Error: Invalid date '{args.date}'. Expected yyyy-mm-dd")
            sys.exit(1)

        config = ConfigLoader()
        setup_logging(config, args.interval, base_datetime)
        logger = logging.getLogger(__name__)
        logger.info("Report Generator System - Starting")
        logger.info(f"Interval: {args.interval} | Base date: {args.date}")

        db_config = config.get_database_config()
        db_service = DatabaseService(db_config)
        db_service.connect()

        try:
            query_executor = QueryExecutor(db_service)
            recipient_service = RecipientService(db_service)
            email_config = config.get_email_config()
            email_service = EmailService(email_config)
            files_config = config.get_files_config()
            csv_generator = CSVGenerator(
                temp_directory=files_config['temp_directory'],
                encoding=files_config['csv_encoding']
            )
            logger_service = LoggerService(db_service)
            date_calculator = DateCalculator()

            report_generator = ReportGenerator(
                db_service=db_service,
                query_executor=query_executor,
                recipient_service=recipient_service,
                email_service=email_service,
                csv_generator=csv_generator,
                logger_service=logger_service,
                date_calculator=date_calculator
            )

            summary = report_generator.process_all_reports(
                interval_name=args.interval,
                base_datetime=base_datetime
            )

            logger.info("=" * 60)
            logger.info("Report Generation Summary:")
            logger.info(f"  Total Reports: {summary['total_reports']}")
            logger.info(f"  Successful: {summary['successful']}")
            logger.info(f"  Failed: {summary['failed']}")
            logger.info("=" * 60)

            sys.exit(1 if summary['failed'] > 0 else 0)

        finally:
            db_service.disconnect()

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
