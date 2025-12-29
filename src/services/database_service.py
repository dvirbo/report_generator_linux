"""
Database Service
Handles Oracle database connections and operations
"""

import logging
from contextlib import contextmanager
from typing import List, Dict, Any

import cx_Oracle as oracledb  # type: ignore

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for Oracle database operations"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database service
        
        Args:
            config: Database configuration dictionary
        """
        self.config = config
        self.connection = None
        self._connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Build Oracle connection string"""
        host = self.config.get('host')
        port = self.config.get('port', 1521)
        service_name = self.config.get('service_name')
        
        # Format: username/password@host:port/service_name
        return f"{host}:{port}/{service_name}"

    def connect(self):
        """Establish database connection"""
        try:
            username = self.config.get('username')
            password = self.config.get('password')
            
            self.connection = oracledb.connect(
                user=username,
                password=password,
                dsn=self._connection_string
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

    @contextmanager
    def get_connection(self):
        """Context manager for database connection"""
        if not self.connection:
            self.connect()
        try:
            yield self.connection
        finally:
            # Don't close connection here, let it be managed externally
            pass

    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dictionaries
        
        Args:
            query: SQL query string with Oracle bind variables
            params: Dictionary of parameters for bind variables
        
        Returns:
            List of dictionaries, each representing a row
        """
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or {})
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch all rows and convert to dictionaries
            results = []
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                results.append(row_dict)
            
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query[:200]}...")
            raise

    def execute_non_query(self, query: str, params: Dict[str, Any] = None) -> int:
        """
        Execute a non-SELECT query (INSERT, UPDATE, DELETE)
        
        Args:
            query: SQL query string
            params: Dictionary of parameters
        
        Returns:
            Number of rows affected
        """
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or {})
            rows_affected = cursor.rowcount
            self.connection.commit()
            cursor.close()
            return rows_affected
        except Exception as e:
            logger.error(f"Non-query execution failed: {e}")
            self.connection.rollback()
            raise

    def commit(self):
        """Commit current transaction"""
        if self.connection:
            self.connection.commit()

    def rollback(self):
        """Rollback current transaction"""
        if self.connection:
            self.connection.rollback()

