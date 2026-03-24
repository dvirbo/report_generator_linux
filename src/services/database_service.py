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
        port = self.config.get('port')
        if port is None:
            raise ValueError("database port must be set in config.ini (e.g. 1521 dev, 1531 UAT)")
        port = int(port)
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
            logger.info("DB connection string: %s user=%s", self._connection_string, username)
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

    def _convert_lob_to_python(self, value: Any) -> Any:
        """
        Convert Oracle LOB objects to Python types
        
        Args:
            value: Value that might be a LOB object
        
        Returns:
            Converted value (CLOB -> str, BLOB -> bytes, others unchanged)
        """
        if value is None:
            return None
        
        # Check if it's a LOB object
        # LOB objects in cx_Oracle have a 'read()' method and are not file-like objects
        # We check the type name to identify LOB objects
        value_type = type(value).__name__
        
        # Check if it's a LOB type (CLOB, BLOB, NCLOB)
        if 'LOB' in value_type.upper() or (hasattr(value, 'read') and not isinstance(value, (str, bytes, int, float, bool))):
            try:
                # Read the LOB content (works for both CLOB and BLOB)
                content = value.read()
                # Close the LOB after reading to free resources
                if hasattr(value, 'close'):
                    try:
                        value.close()
                    except:
                        pass  # Ignore errors on close
                return content
            except Exception as e:
                logger.warning(f"Failed to read LOB content (type: {value_type}): {e}, returning string representation")
                # Try to close even if read failed
                if hasattr(value, 'close'):
                    try:
                        value.close()
                    except:
                        pass
                return str(value)
        
        return value

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
                # Convert LOB objects to Python types before creating dictionary
                converted_row = [self._convert_lob_to_python(value) for value in row]
                row_dict = dict(zip(columns, converted_row))
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
            # Log the statement so it's clear which operation failed
            query_preview = (query.strip()[:200] + '...') if len(query.strip()) > 200 else query.strip()
            logger.error(f"Non-query execution failed: {e}")
            logger.error(f"Statement: {query_preview}")
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
