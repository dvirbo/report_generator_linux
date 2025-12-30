"""
Logger Service
Centralized logging to database and files
"""

import logging
import json
import traceback
from typing import Dict, Any, Optional
from .database_service import DatabaseService
import cx_Oracle as oracledb

logger = logging.getLogger(__name__)

STATUS_RUNNING = "RUNNING"


class LoggerService:
    """Service for logging operations"""

    def __init__(self, db_service: DatabaseService):
        """
        Initialize logger service
        
        Args:
            db_service: DatabaseService instance
        """
        self.db_service = db_service

    def log_execution_start(self, report_id: int) -> int:
        """
        Insert a new execution row and return its generated execution_id.
        Args:
            report_id: Identifier of the report being executed.
        Returns:
            The auto-generated execution_id from report_execution_log.
        Raises:
            RuntimeError: If the execution_id cannot be retrieved after insert.
            oracledb.DatabaseError: Propagated when the insert fails even after rollback.
        """

        insert_sql = """
            INSERT INTO report_execution_log (
                report_id,
                execution_start,
                status
            )
            VALUES (:report_id, SYSDATE, :status)
            RETURNING execution_id INTO :out_id
        """
        with self.db_service.get_connection() as conn:
            cur = conn.cursor()
            out_id = cur.var(oracledb.NUMBER)
            try:
                cur.execute(insert_sql, {
                    'report_id': report_id,
                    'status': STATUS_RUNNING,
                    'out_id': out_id
                })
                conn.commit()
            except oracledb.DatabaseError as e:
                conn.rollback()
                raise
            finally:
                cur.close()

            execution_id = out_id.getvalue()
            if execution_id is None:
                raise RuntimeError("Failed to retrieve execution_id")
            # Handle case where getvalue() returns a list (shouldn't happen but can occur)
            if isinstance(execution_id, list):
                if len(execution_id) > 0:
                    execution_id = execution_id[0]
                else:
                    raise RuntimeError("execution_id is an empty list")
            return int(execution_id)



    def log_execution_end(
        self,
        execution_id: int,
        status: str,
        details: Dict[str, Any]
    ):
        """
        Log execution end
        
        Args:
            execution_id: Execution ID
            status: Status (SUCCESS/FAILED/PARTIAL)
            details: Dictionary with execution details
        """
        query = """
            UPDATE report_execution_log
            SET execution_end = SYSDATE,
                status = :status,
                records_returned = :records_returned,
                recipients_count = :recipients_count,
                error_message = :error_message,
                error_stack = :error_stack,
                query_params = :query_params
            WHERE execution_id = :execution_id
        """
        
        try:
            params = {
                'execution_id': execution_id,
                'status': status,
                'records_returned': details.get('records_returned'),
                'recipients_count': details.get('recipients_count'),
                'error_message': details.get('error_message'),
                'error_stack': details.get('error_stack'),
                'query_params': json.dumps(details.get('query_params')) if details.get('query_params') else None
            }
            
            self.db_service.execute_non_query(query, params)
            self.db_service.commit()
            
            logger.info(f"Completed execution {execution_id} with status {status}")
            
        except Exception as e:
            logger.error(f"Failed to log execution end: {e}")
            self.db_service.rollback()

    def log_email_delivery(
        self,
        execution_id: int,
        report_id: int,
        recipient_email: str,
        recipient_name: Optional[str],
        bu_internal_id: Optional[int],
        status: str,
        error_message: Optional[str] = None,
        email_size_kb: Optional[int] = None
    ):
        """
        Log email delivery
        
        Args:
            execution_id: Execution ID
            report_id: Report ID
            recipient_email: Recipient email address
            recipient_name: Recipient name
            bu_internal_id: BU internal ID
            status: Delivery status (SENT/FAILED/BOUNCED)
            error_message: Error message if failed
            email_size_kb: Email size in KB
        """
        query = """
            INSERT INTO report_email_delivery_log
            (execution_id, report_id, recipient_email, recipient_name, bu_internal_id,
             sent_timestamp, delivery_status, error_message, email_size_kb)
            VALUES (:execution_id, :report_id, :recipient_email, :recipient_name, :bu_internal_id,
                    SYSDATE, :delivery_status, :error_message, :email_size_kb)
        """
        
        try:
            params = {
                'execution_id': execution_id,
                'report_id': report_id,
                'recipient_email': recipient_email,
                'recipient_name': recipient_name,
                'bu_internal_id': bu_internal_id,
                'delivery_status': status,
                'error_message': error_message,
                'email_size_kb': email_size_kb
            }
            
            self.db_service.execute_non_query(query, params)
            self.db_service.commit()
            
            logger.debug(f"Logged email delivery: {recipient_email} - {status}")
            
        except Exception as e:
            # Check if it's a "table does not exist" error
            error_msg = str(e)
            if 'ORA-00942' in error_msg or 'table or view does not exist' in error_msg.lower():
                logger.warning(f"Table report_email_delivery_log does not exist. Email delivery logging skipped.")
                logger.warning(f"To enable email delivery logging, create the report_email_delivery_log table.")
                # Don't raise - allow the process to continue without logging
            else:
                logger.error(f"Failed to log email delivery: {e}")
                self.db_service.rollback()
                # Don't raise - email delivery logging failure shouldn't stop the process

    def log_error(self, execution_id: int, error: Exception):
        """
        Log error details
        
        Args:
            execution_id: Execution ID
            error: Exception object
        """
        error_message = str(error)
        error_stack = traceback.format_exc()
        
        query = """
            UPDATE report_execution_log
            SET error_message = :error_message,
                error_stack = :error_stack
            WHERE execution_id = :execution_id
        """
        
        try:
            params = {
                'execution_id': execution_id,
                'error_message': error_message,
                'error_stack': error_stack
            }
            
            self.db_service.execute_non_query(query, params)
            self.db_service.commit()
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
            self.db_service.rollback()


