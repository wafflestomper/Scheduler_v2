"""
Base processor for CSV data handling with common functionality 
for validation and processing.
"""
from typing import List, Dict, Any, Tuple
import csv


class BaseProcessor:
    """Base class for CSV data processors"""
    
    @classmethod
    def get_expected_headers(cls) -> List[str]:
        """Return the expected CSV headers for this processor"""
        raise NotImplementedError("Subclasses must implement this method")
    
    @classmethod
    def process_row(cls, row: List[str], line_num: int) -> Dict[str, Any]:
        """Process a single row from the CSV file
        
        Args:
            row: The CSV row as a list of strings
            line_num: The line number in the CSV file (for error reporting)
            
        Returns:
            Dictionary with processed data and any errors
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    @classmethod
    def process_csv(cls, reader: csv.reader) -> Dict[str, Any]:
        """Process multiple rows from a CSV reader
        
        Args:
            reader: CSV reader object (after header row has been consumed)
            
        Returns:
            Dictionary with counts of created, updated objects and any errors
        """
        created, updated, errors = 0, 0, []
        
        for i, row in enumerate(reader, start=2):  # Start from 2 for line number (after header)
            try:
                if not any(row):  # Skip empty rows
                    continue
                
                result = cls.process_row(row, i)
                
                if result.get('error'):
                    errors.append(result['error'])
                    continue
                    
                if result.get('created'):
                    created += 1
                elif result.get('updated'):
                    updated += 1
                    
            except Exception as e:
                errors.append(f'Line {i}: Unexpected error: {str(e)}')
        
        return {'created': created, 'updated': updated, 'errors': errors}
    
    @classmethod
    def get_field_value(cls, row: List[str], index: int, default=None, required: bool = False) -> Tuple[Any, str]:
        """Helper method to extract field values from CSV rows
        
        Args:
            row: CSV row as list of strings
            index: Index of the field in the row
            default: Default value if field is empty
            required: Whether the field is required
            
        Returns:
            Tuple of (value, error_message)
            If required and missing, error_message will be set
            Otherwise, error_message will be None
        """
        value = row[index].strip() if index < len(row) and row[index].strip() else default
        
        if required and not value:
            field_name = cls.get_expected_headers()[index]
            return None, f'Missing required field: {field_name}'
            
        return value, None 