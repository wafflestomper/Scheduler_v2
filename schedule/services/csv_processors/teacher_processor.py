"""
Teacher CSV data processor
"""
from typing import List, Dict, Any
from ...models import Teacher
from .base_processor import BaseProcessor


class TeacherProcessor(BaseProcessor):
    """Process CSV data for Teacher records"""
    
    @classmethod
    def get_expected_headers(cls) -> List[str]:
        """Return the expected CSV headers for teacher data"""
        return ['teacher_id', 'first_name', 'last_name', 'availability', 'subjects']
    
    @classmethod
    def process_row(cls, row: List[str], line_num: int) -> Dict[str, Any]:
        """Process a single row of teacher data from CSV
        
        Args:
            row: The CSV row as a list of strings
            line_num: The line number in the CSV file (for error reporting)
            
        Returns:
            Dictionary with processing results and any errors
        """
        result = {'created': False, 'updated': False, 'error': None}
        
        # Get field values with validation
        teacher_id, error = cls.get_field_value(row, 0, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        first_name, error = cls.get_field_value(row, 1, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        last_name, error = cls.get_field_value(row, 2, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        availability, _ = cls.get_field_value(row, 3, default="")
        subjects, _ = cls.get_field_value(row, 4, default="")
        
        # Construct full name
        name = f"{first_name} {last_name}"
        
        # Create or update teacher
        try:
            teacher, created = Teacher.objects.update_or_create(
                id=teacher_id,
                defaults={
                    'name': name,
                    'availability': availability,
                    'subjects': subjects
                }
            )
            result['created'] = created
            result['updated'] = not created
            
        except Exception as e:
            result['error'] = f'Line {line_num}: Error processing teacher: {str(e)}'
            
        return result 