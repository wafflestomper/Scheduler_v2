"""
Room CSV data processor
"""
from typing import List, Dict, Any
from ...models import Room
from .base_processor import BaseProcessor


class RoomProcessor(BaseProcessor):
    """Process CSV data for Room records"""
    
    @classmethod
    def get_expected_headers(cls) -> List[str]:
        """Return the expected CSV headers for room data"""
        return ['room_id', 'number', 'capacity', 'type']
    
    @classmethod
    def process_row(cls, row: List[str], line_num: int) -> Dict[str, Any]:
        """Process a single row of room data from CSV
        
        Args:
            row: The CSV row as a list of strings
            line_num: The line number in the CSV file (for error reporting)
            
        Returns:
            Dictionary with processing results and any errors
        """
        result = {'created': False, 'updated': False, 'error': None}
        
        # Get field values with validation
        room_id, error = cls.get_field_value(row, 0, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        number, error = cls.get_field_value(row, 1, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        capacity_str, _ = cls.get_field_value(row, 2, default="30")
        room_type, _ = cls.get_field_value(row, 3, default="classroom")
        
        # Parse capacity
        try:
            capacity = int(capacity_str) if capacity_str else 30
        except ValueError:
            result['error'] = f'Line {line_num}: Invalid capacity, must be a number'
            return result
        
        # Create or update room
        try:
            room, created = Room.objects.update_or_create(
                id=room_id,
                defaults={
                    'number': number,
                    'capacity': capacity,
                    'type': room_type
                }
            )
            result['created'] = created
            result['updated'] = not created
            
        except Exception as e:
            result['error'] = f'Line {line_num}: Error processing room: {str(e)}'
            
        return result 