"""
Query Executor
Execute parameterized Oracle PL/SQL queries safely
"""

import logging
from typing import List, Dict, Any
from datetime import date, datetime
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
            bu_patterns = [r':BU\b', r':BU[_\s]*IDENTIFIER']
            manager_patterns = [r':MANAGER[_\s]*ID', r':MENAHEL[_\s]*ID']
            
            query_has_start = any(re.search(pattern, query_upper) for pattern in start_patterns)
            query_has_end = any(re.search(pattern, query_upper) for pattern in end_patterns)
            query_has_bu = any(re.search(pattern, query_upper) for pattern in bu_patterns)
            query_has_manager = any(re.search(pattern, query_upper) for pattern in manager_patterns)
            
            # Validate only parameters that are actually used in the query
            if query_has_start or query_has_end:
                self._validate_params(params, query_has_start, query_has_end, requires_bu and query_has_bu, query_has_manager)
            
            # Only include parameters that are actually in the query
            oracle_params = self._prepare_params(params, query_template, query_has_start, query_has_end, query_has_bu, query_has_manager)
            
            # Execute query
            logger.debug(f"Executing query with params: {oracle_params}")
            logger.debug(f"Query uses bind variables - start_date: {query_has_start}, end_date: {query_has_end}, bu: {query_has_bu}, manager_id: {query_has_manager}")
            results = self.db_service.execute_query(query_template, oracle_params)
            
            logger.info(f"Query returned {len(results)} rows")
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def _validate_params(self, params: Dict[str, Any], query_has_start: bool, query_has_end: bool, requires_bu: bool, query_has_manager: bool = False):
        '''
        Validate query parameters before executing the query
        
        Args:
            params: Dictionary of parameters (:start_date, :end_date, :bu, :manager_id, :bu_identifier)
            query_has_start: Whether query uses :start_date bind variable
            query_has_end: Whether query uses :end_date bind variable
            requires_bu: Whether :bu parameter is required
            query_has_manager: Whether query uses :manager_id bind variable
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
            if 'bu' not in params and 'bu_identifier' not in params:
                raise ValueError("Missing required parameter: bu or bu_identifier")
        
        # Validate manager_id if query uses it (but it can be None/NULL for optional filtering)
        # Note: manager_id is optional - queries may use (:manager_id IS NULL OR ...) pattern
        # So we don't require it to be present, but if it is, we'll use it
        
        # Validate date range if both are used
        if query_has_start and query_has_end:
            start = params['start_date'].date() if hasattr(params['start_date'], 'date') else params['start_date']
            end = params['end_date'].date() if hasattr(params['end_date'], 'date') else params['end_date']
            if start > end:
                raise ValueError("start_date must be <= end_date")

    def _prepare_params(self, params: Dict[str, Any], query_template: str, 
                       query_has_start: bool, query_has_end: bool, query_has_bu: bool, query_has_manager: bool = False) -> Dict[str, Any]:
        """
        Prepare parameters for Oracle bind variables
        Only include parameters that are actually used in the query
        
        Args:
            params: Dictionary of available parameters
            query_template: SQL query string to check for bind variables
            query_has_start: Whether query uses start date bind variable
            query_has_end: Whether query uses end date bind variable
            query_has_bu: Whether query uses bu bind variable
            query_has_manager: Whether query uses manager_id bind variable
        
        Returns:
            Dictionary of parameters that are actually used in the query
            Note: Oracle bind variables are case-insensitive, so we map to the actual variable name in the query
        """
        oracle_params = {}
        import re
        
        # Check if query uses TO_DATE with date format strings (e.g., TO_DATE(:StartDate, 'DD/MM/YYYY'))
        # If so, we need to pass dates as formatted strings instead of datetime objects
        # Pattern matches: TO_DATE(:StartDate, 'DD/MM/YYYY') or TO_DATE(:start_date, 'DD/MM/YYYY') etc.
        # Look for TO_DATE( followed by any bind variable containing 'start' and 'date', then 'DD/MM/YYYY'
        to_date_pattern_start = r'TO_DATE\s*\(\s*:[^,\s)]*start[^,\s)]*date[^,\s)]*\s*,\s*[\'"]DD/MM/YYYY[\'"]'
        query_uses_to_date_start = bool(re.search(to_date_pattern_start, query_template, re.IGNORECASE))
        to_date_pattern_end = r'TO_DATE\s*\(\s*:[^,\s)]*end[^,\s)]*date[^,\s)]*\s*,\s*[\'"]DD/MM/YYYY[\'"]'
        query_uses_to_date_end = bool(re.search(to_date_pattern_end, query_template, re.IGNORECASE))
        query_uses_to_date = query_uses_to_date_start or query_uses_to_date_end
        
        # Oracle bind variables are case-insensitive, but cx_Oracle may need exact match
        # Find the actual bind variable names in the query and use them as-is
        if query_has_start:
            # Find the actual bind variable name (could be :StartDate, :START_DATE, :start_date, etc.)
            start_matches = list(re.finditer(r':(\w*start\w*date\w*)', query_template, re.IGNORECASE))
            if start_matches:
                # Get the first match and extract the variable name (without the colon)
                actual_var_name = start_matches[0].group(1)  # group(1) is the name without :
                # Check if this variable is used with TO_DATE - if so, format as string
                start_date_val = params['start_date']
                if query_uses_to_date_start and (isinstance(start_date_val, datetime) or isinstance(start_date_val, date)):
                    # Format date as DD/MM/YYYY string for TO_DATE function
                    if isinstance(start_date_val, datetime):
                        start_date_val = start_date_val.date()
                    oracle_params[actual_var_name] = start_date_val.strftime('%d/%m/%Y')
                    logger.debug(f"Formatting start_date as DD/MM/YYYY string for TO_DATE: {oracle_params[actual_var_name]}")
                else:
                    # Pass datetime/date object directly (Oracle handles it natively)
                    oracle_params[actual_var_name] = start_date_val
                logger.debug(f"Mapping start_date parameter to bind variable: {actual_var_name}")
            else:
                # Fallback: try common variations (lowercase)
                if query_uses_to_date_start and (isinstance(params['start_date'], datetime) or isinstance(params['start_date'], date)):
                    date_val = params['start_date']
                    if isinstance(date_val, datetime):
                        date_val = date_val.date()
                    oracle_params['startdate'] = date_val.strftime('%d/%m/%Y')
                else:
                    oracle_params['startdate'] = params['start_date']
        
        if query_has_end:
            # Find the actual bind variable name
            end_matches = list(re.finditer(r':(\w*end\w*date\w*)', query_template, re.IGNORECASE))
            if end_matches:
                actual_var_name = end_matches[0].group(1)
                # Check if this variable is used with TO_DATE - if so, format as string
                end_date_val = params['end_date']
                if query_uses_to_date_end and (isinstance(end_date_val, datetime) or isinstance(end_date_val, date)):
                    # Format date as DD/MM/YYYY string for TO_DATE function
                    if isinstance(end_date_val, datetime):
                        end_date_val = end_date_val.date()
                    oracle_params[actual_var_name] = end_date_val.strftime('%d/%m/%Y')
                    logger.debug(f"Formatting end_date as DD/MM/YYYY string for TO_DATE: {oracle_params[actual_var_name]}")
                else:
                    # Pass datetime/date object directly (Oracle handles it natively)
                    oracle_params[actual_var_name] = end_date_val
                logger.debug(f"Mapping end_date parameter to bind variable: {actual_var_name}")
            else:
                # Fallback: try common variations (lowercase)
                if query_uses_to_date_end and (isinstance(params['end_date'], datetime) or isinstance(params['end_date'], date)):
                    date_val = params['end_date']
                    if isinstance(date_val, datetime):
                        date_val = date_val.date()
                    oracle_params['enddate'] = date_val.strftime('%d/%m/%Y')
                else:
                    oracle_params['enddate'] = params['end_date']
        
        if query_has_bu:
            # Check for :bu_identifier first, then :bu
            if 'bu_identifier' in params:
                bu_identifier_matches = list(re.finditer(r':(\w*bu[_\s]*identifier\w*)', query_template, re.IGNORECASE))
                if bu_identifier_matches:
                    actual_var_name = bu_identifier_matches[0].group(1)
                    oracle_params[actual_var_name] = params['bu_identifier']
                    logger.debug(f"Mapping bu_identifier parameter to bind variable: {actual_var_name}")
                else:
                    # Fallback to :bu if :bu_identifier not found in query
                    bu_matches = list(re.finditer(r':(\w*bu\w*)', query_template, re.IGNORECASE))
                    if bu_matches:
                        actual_var_name = bu_matches[0].group(1)
                        oracle_params[actual_var_name] = params['bu_identifier']
                    else:
                        oracle_params['bu_identifier'] = params['bu_identifier']
            elif 'bu' in params:
                bu_matches = list(re.finditer(r':(\w*bu\w*)', query_template, re.IGNORECASE))
                if bu_matches:
                    actual_var_name = bu_matches[0].group(1)
                    oracle_params[actual_var_name] = params['bu']
                    logger.debug(f"Mapping bu parameter to bind variable: {actual_var_name}")
                else:
                    oracle_params['bu'] = params['bu']
        
        if query_has_manager:
            # manager_id is optional - queries may use (:manager_id IS NULL OR ...) pattern
            # Only include it if it's provided in params, otherwise pass None
            if 'manager_id' in params:
                # Find the actual bind variable name (could be :manager_id, :ManagerId, :MENAHEL_ID, etc.)
                manager_matches = list(re.finditer(r':(\w*manager\w*id\w*|\w*menahel\w*id\w*)', query_template, re.IGNORECASE))
                if manager_matches:
                    actual_var_name = manager_matches[0].group(1)
                    oracle_params[actual_var_name] = params['manager_id']
                    logger.debug(f"Mapping manager_id parameter to bind variable: {actual_var_name}")
                else:
                    # Fallback: try common variations
                    oracle_params['manager_id'] = params['manager_id']
            else:
                # If manager_id is not provided but query uses it, pass None
                # This allows queries with (:manager_id IS NULL OR ...) to work
                manager_matches = list(re.finditer(r':(\w*manager\w*id\w*|\w*menahel\w*id\w*)', query_template, re.IGNORECASE))
                if manager_matches:
                    actual_var_name = manager_matches[0].group(1)
                    oracle_params[actual_var_name] = None
                    logger.debug(f"Query uses manager_id but parameter not provided, passing NULL to bind variable: {actual_var_name}")
        
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

