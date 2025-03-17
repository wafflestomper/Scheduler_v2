"""
Period CSV data processor
"""
from typing import List, Dict, Any
from datetime import datetime
from ...models import Period
from .base_processor import BaseProcessor


class PeriodProcessor(BaseProcessor):
    """Process CSV data for Period records"""
    
    @classmethod
    def get_expected_headers(cls) -> List[str]:
        """Return the expected CSV headers for period data"""
        return ['period_id', 'period_name', 'days', 'slot', 'start_time', 'end_time']
    
    @classmethod
    def process_row(cls, row: List[str], line_num: int) -> Dict[str, Any]:
        """Process a single row of period data from CSV
        
        Args:
            row: The CSV row as a list of strings
            line_num: The line number in the CSV file (for error reporting)
            
        Returns:
            Dictionary with processing results and any errors
        """
        result = {'created': False, 'updated': False, 'error': None}
        
        # Get field values with validation
        period_id, error = cls.get_field_value(row, 0, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        period_name, _ = cls.get_field_value(row, 1)
        days, _ = cls.get_field_value(row, 2, default="M")
        
        slot, error = cls.get_field_value(row, 3, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        start_time_str, error = cls.get_field_value(row, 4, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        end_time_str, error = cls.get_field_value(row, 5, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
        
        # Parse times 
        try:
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        except ValueError:
            result['error'] = f'Line {line_num}: Invalid start time format, should be HH:MM'
            return result
            
        try:
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            result['error'] = f'Line {line_num}: Invalid end time format, should be HH:MM'
            return result
        
        # Create or update period
        try:
            period, created = Period.objects.update_or_create(
                id=period_id,
                defaults={
                    'period_name': period_name,
                    'days': days,
                    'slot': slot,
                    'start_time': start_time,
                    'end_time': end_time
                }
            )
            result['created'] = created
            result['updated'] = not created
            
        except Exception as e:
            result['error'] = f'Line {line_num}: Error processing period: {str(e)}'
            
        return result 