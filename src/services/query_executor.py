"""
Query Executor
Execute parameterized Oracle PL/SQL queries safely
"""

import logging
from typing import List, Dict, Any
from datetime import date
from .database_service import DatabaseService

logger = logging.getLogger(__name__)


class QueryExecutor:
    def __init__(self, db_service: DatabaseService):
        """
        Initialize query executor
        
        Args:
            db_service: DatabaseService instance
        """
        self.db_service = db_service

    def execute_query(
        self,
        query_template: str,
        params: Dict[str, Any],
        requires_bu: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute parameterized query with Oracle bind variables
        
        Args:
            query_template: SQL query template with :param bind variables
            params: Dictionary of parameters (:start_date, :end_date, :bu)
            requires_bu: Whether :bu parameter is required
        
        Returns:
            List of dictionaries representing query results
        """
        try:
            # Validate parameters
            self._validate_params(params, requires_bu)
            
            # Convert date objects to Oracle date format if needed
            oracle_params = self._prepare_params(params)
            
            # Execute query
            logger.debug(f"Executing query with params: {oracle_params}")
            results = self.db_service.execute_query(query_template, oracle_params)
            
            logger.info(f"Query returned {len(results)} rows")
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def _validate_params(self, params: Dict[str, Any], requires_bu: bool):
        '''
        Validate query parameters before executing the query
        
        Args:
            params: Dictionary of parameters (:start_date, :end_date, :bu)
            requires_bu: Whether :bu parameter is required
        '''
        required_params = ['start_date', 'end_date']
        if requires_bu:
            required_params.append('bu')
        
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Validate date parameters
        if not isinstance(params['start_date'], date):
            raise ValueError("start_date must be a date object")
        if not isinstance(params['end_date'], date):
            raise ValueError("end_date must be a date object")
        if params['start_date'] > params['end_date']:
            raise ValueError("start_date must be <= end_date")

    def _prepare_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare parameters for Oracle bind variables
        Convert date objects to appropriate format
        """
        oracle_params = {}
        
        # Oracle accepts Python date objects directly
        oracle_params['start_date'] = params['start_date']
        oracle_params['end_date'] = params['end_date']
         
        if 'bu' in params:
            oracle_params['bu'] = params['bu']
        
        return oracle_params

    def validate_query_result(self, result: List[Dict[str, Any]]) -> bool:
        """
        Validate query result
        
        Args:
            result: Query result list
        
        Returns:
            True if valid
        """
        if not isinstance(result, list):
            return False
        
        # Check if all items are dictionaries
        return all(isinstance(row, dict) for row in result)

