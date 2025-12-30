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
            # Check which bind variables are actually in the query
            # Handle various case variations: :start_date, :StartDate, :STARTDATE, etc.
            import re
            query_upper = query_template.upper()
            
            # Use regex to find bind variables (case-insensitive)
            # Pattern matches :variable_name or :VARIABLE_NAME (Oracle is case-insensitive for bind vars)
            start_patterns = [r':START[_\s]*DATE', r':STARTDATE']
            end_patterns = [r':END[_\s]*DATE', r':ENDDATE']
            bu_patterns = [r':BU\b']
            
            query_has_start = any(re.search(pattern, query_upper) for pattern in start_patterns)
            query_has_end = any(re.search(pattern, query_upper) for pattern in end_patterns)
            query_has_bu = any(re.search(pattern, query_upper) for pattern in bu_patterns)
            
            # Validate only parameters that are actually used in the query
            if query_has_start or query_has_end:
                self._validate_params(params, query_has_start, query_has_end, requires_bu and query_has_bu)
            
            # Only include parameters that are actually in the query
            oracle_params = self._prepare_params(params, query_template, query_has_start, query_has_end, query_has_bu)
            
            # Execute query
            logger.debug(f"Executing query with params: {oracle_params}")
            logger.debug(f"Query uses bind variables - start_date: {query_has_start}, end_date: {query_has_end}, bu: {query_has_bu}")
            results = self.db_service.execute_query(query_template, oracle_params)
            
            logger.info(f"Query returned {len(results)} rows")
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def _validate_params(self, params: Dict[str, Any], query_has_start: bool, query_has_end: bool, requires_bu: bool):
        '''
        Validate query parameters before executing the query
        
        Args:
            params: Dictionary of parameters (:start_date, :end_date, :bu)
            query_has_start: Whether query uses :start_date bind variable
            query_has_end: Whether query uses :end_date bind variable
            requires_bu: Whether :bu parameter is required
        '''
        from datetime import datetime
        
        # Validate start_date if query uses it
        if query_has_start:
            if 'start_date' not in params:
                raise ValueError("Missing required parameter: start_date")
            # Convert datetime to date if needed
            start_val = params['start_date']
            if isinstance(start_val, datetime):
                params['start_date'] = start_val.date()
            elif not isinstance(start_val, date):
                raise ValueError("start_date must be a date or datetime object")
        
        # Validate end_date if query uses it
        if query_has_end:
            if 'end_date' not in params:
                raise ValueError("Missing required parameter: end_date")
            # Convert datetime to date if needed
            end_val = params['end_date']
            if isinstance(end_val, datetime):
                params['end_date'] = end_val.date()
            elif not isinstance(end_val, date):
                raise ValueError("end_date must be a date or datetime object")
        
        # Validate bu if required
        if requires_bu:
            if 'bu' not in params:
                raise ValueError("Missing required parameter: bu")
        
        # Validate date range if both are used
        if query_has_start and query_has_end:
            start = params['start_date'].date() if hasattr(params['start_date'], 'date') else params['start_date']
            end = params['end_date'].date() if hasattr(params['end_date'], 'date') else params['end_date']
            if start > end:
                raise ValueError("start_date must be <= end_date")

    def _prepare_params(self, params: Dict[str, Any], query_template: str, 
                       query_has_start: bool, query_has_end: bool, query_has_bu: bool) -> Dict[str, Any]:
        """
        Prepare parameters for Oracle bind variables
        Only include parameters that are actually used in the query
        
        Args:
            params: Dictionary of available parameters
            query_template: SQL query string to check for bind variables
            query_has_start: Whether query uses start date bind variable
            query_has_end: Whether query uses end date bind variable
            query_has_bu: Whether query uses bu bind variable
        
        Returns:
            Dictionary of parameters that are actually used in the query
            Note: Oracle bind variables are case-insensitive, so we map to the actual variable name in the query
        """
        oracle_params = {}
        import re
        
        # Oracle bind variables are case-insensitive, but cx_Oracle may need exact match
        # Find the actual bind variable names in the query and use them as-is
        if query_has_start:
            # Find the actual bind variable name (could be :StartDate, :START_DATE, :start_date, etc.)
            start_matches = list(re.finditer(r':(\w*start\w*date\w*)', query_template, re.IGNORECASE))
            if start_matches:
                # Get the first match and extract the variable name (without the colon)
                actual_var_name = start_matches[0].group(1)  # group(1) is the name without :
                # Use the exact name from the query - Oracle is case-insensitive but cx_Oracle may need it
                oracle_params[actual_var_name] = params['start_date']
                logger.debug(f"Mapping start_date parameter to bind variable: {actual_var_name}")
            else:
                # Fallback: try common variations (lowercase)
                oracle_params['startdate'] = params['start_date']
        
        if query_has_end:
            # Find the actual bind variable name
            end_matches = list(re.finditer(r':(\w*end\w*date\w*)', query_template, re.IGNORECASE))
            if end_matches:
                actual_var_name = end_matches[0].group(1)
                oracle_params[actual_var_name] = params['end_date']
                logger.debug(f"Mapping end_date parameter to bind variable: {actual_var_name}")
            else:
                # Fallback: try common variations (lowercase)
                oracle_params['enddate'] = params['end_date']
        
        if query_has_bu and 'bu' in params:
            bu_matches = list(re.finditer(r':(\w*bu\w*)', query_template, re.IGNORECASE))
            if bu_matches:
                actual_var_name = bu_matches[0].group(1)
                oracle_params[actual_var_name] = params['bu']
            else:
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

