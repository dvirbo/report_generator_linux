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


