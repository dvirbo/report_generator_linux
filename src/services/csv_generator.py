"""
CSV Generator
Generate CSV files from query results
"""

import csv
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CSVGenerator:
    """
    Generate CSV files from query results
    
    >>> import tempfile
    >>> import os
    >>> from pathlib import Path
    >>> 
    >>> # Test CSV generation with data
    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     generator = CSVGenerator(temp_directory=tmpdir)
    ...     data = [
    ...         {'name': 'John', 'age': 30, 'city': 'New York'},
    ...         {'name': 'Jane', 'age': 25, 'city': 'Boston'}
    ...     ]
    ...     csv_path = generator.generate_csv(data, 'Test Report', '20250101_120000')
    ...     assert os.path.exists(csv_path)
    ...     assert 'Test_Report' in csv_path
    ...     assert '20250101_120000' in csv_path
    ...     # Verify CSV content
    ...     with open(csv_path, 'r', encoding='utf-8-sig') as f:
    ...         lines = f.readlines()
    ...         assert 'name,age,city' in lines[0]
    ...         assert 'John,30,New York' in lines[1]
    ... 
    >>> # Test empty data handling
    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     generator = CSVGenerator(temp_directory=tmpdir)
    ...     csv_path = generator.generate_csv([], 'Empty Report', '20250101_120000')
    ...     assert os.path.exists(csv_path)
    ...     with open(csv_path, 'r', encoding='utf-8-sig') as f:
    ...         content = f.read()
    ...         assert 'No data available' in content
    ... 
    >>> # Test filename generation
    >>> generator = CSVGenerator()
    >>> filename = generator.get_csv_filename('Test Report Name', '20250101_120000')
    >>> 'Test_Report_Name' in filename
    True
    >>> '20250101_120000' in filename
    True
    >>> 
    >>> # Test data validation
    >>> generator.validate_csv_data([{'a': 1}, {'a': 2}])
    True
    >>> generator.validate_csv_data([])
    True
    >>> generator.validate_csv_data([{'a': 1}, {'b': 2}])
    False
    >>> generator.validate_csv_data('not a list')
    False
    """

    def __init__(self, temp_directory: str = "temp", encoding: str = "utf-8-sig"):
        """
        Initialize CSV generator
        
        Args:
            temp_directory: Directory for temporary CSV files
            encoding: CSV file encoding (utf-8-sig for Excel compatibility)
        """
        self.temp_directory = Path(temp_directory)
        self.encoding = encoding
        self._ensure_temp_directory()

    def _ensure_temp_directory(self):
        """Ensure temp directory exists"""
        self.temp_directory.mkdir(parents=True, exist_ok=True)

    def _get_date_directory(self, date: datetime = None) -> Path:
        """
        Get or create date-based subdirectory for CSV files
        
        Args:
            date: Date to use for directory (defaults to current date)
        
        Returns:
            Path to date-based directory
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y%m%d")
        date_dir = self.temp_directory / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir

    def generate_csv(
        self,
        data: List[Dict[str, Any]],
        report_name: str,
        timestamp: str = None
    ) -> str:
        """
        Generate CSV file from query results
        
        Args:
            data: List of dictionaries representing query results
            report_name: Report name for filename
            timestamp: Timestamp string (defaults to current timestamp)
        
        Returns:
            Path to generated CSV file
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract date from timestamp or use current date
        try:
            # Try to parse date from timestamp (format: YYYYMMDD_HHMMSS)
            date_obj = datetime.strptime(timestamp[:8], "%Y%m%d")
        except (ValueError, IndexError):
            # Fallback to current date if parsing fails
            date_obj = datetime.now()
        
        # Get date-based directory for this CSV file
        date_dir = self._get_date_directory(date_obj)
        
        filename = self.get_csv_filename(report_name, timestamp)
        filepath = date_dir / filename
        
        try:
            if not data:
                # Create empty file for no data case
                with open(filepath, 'w', encoding=self.encoding, newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['No data available for the selected period.'])
                logger.info(f"Generated empty CSV file: {filepath}")
            else:
                # Get column names from first row
                fieldnames = list(data[0].keys())
                
                # Write CSV with UTF-8 BOM for Excel compatibility
                with open(filepath, 'w', encoding=self.encoding, newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                
                logger.info(f"Generated CSV file: {filepath} with {len(data)} rows")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate CSV file: {e}")
            raise

    def get_csv_filename(self, report_name: str, timestamp: str) -> str:
        """
        Generate standardized CSV filename
        
        Args:
            report_name: Report name
            timestamp: Timestamp string
        
        Returns:
            CSV filename
        """
        # Sanitize report name for filename
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in report_name)
        return f"report_{safe_name}_{timestamp}.csv"

    def validate_csv_data(self, data: List[Dict[str, Any]]) -> bool:
        """
        Validate data before CSV generation
        
        Args:
            data: List of dictionaries
        
        Returns:
            True if valid
        """
        if not isinstance(data, list):
            return False
        
        if not data:
            return True  # Empty data is valid
        
        # Check if all items are dictionaries
        if not all(isinstance(row, dict) for row in data):
            return False
        
        # Check if all dictionaries have the same keys
        first_keys = set(data[0].keys())
        return all(set(row.keys()) == first_keys for row in data)

    def cleanup_file(self, filepath: str):
        """
        Remove temporary CSV file
        
        Args:
            filepath: Path to file to remove
        
        >>> import tempfile
        >>> import os
        >>> 
        >>> # Test file cleanup
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     generator = CSVGenerator(temp_directory=tmpdir)
        ...     csv_path = generator.generate_csv([{'test': 'data'}], 'Test', '20250101_120000')
        ...     assert os.path.exists(csv_path)
        ...     generator.cleanup_file(csv_path)
        ...     assert not os.path.exists(csv_path)
        """
        try:
            file_path = Path(filepath)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up temporary file: {filepath}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {filepath}: {e}")
