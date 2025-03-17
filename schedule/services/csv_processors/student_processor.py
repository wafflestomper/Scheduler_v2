"""
Student CSV data processor
"""
from typing import List, Dict, Any
from ...models import Student
from .base_processor import BaseProcessor


class StudentProcessor(BaseProcessor):
    """Process CSV data for Student records"""
    
    @classmethod
    def get_expected_headers(cls) -> List[str]:
        """Return the expected CSV headers for student data"""
        return ['student_id', 'first_name', 'nickname', 'last_name', 'grade_level']
    
    @classmethod
    def process_row(cls, row: List[str], line_num: int) -> Dict[str, Any]:
        """Process a single row of student data from CSV
        
        Args:
            row: The CSV row as a list of strings
            line_num: The line number in the CSV file (for error reporting)
            
        Returns:
            Dictionary with processing results and any errors
        """
        result = {'created': False, 'updated': False, 'error': None}
        
        # Get field values with validation
        student_id, error = cls.get_field_value(row, 0, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        first_name, error = cls.get_field_value(row, 1, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        nickname, _ = cls.get_field_value(row, 2)
        
        last_name, error = cls.get_field_value(row, 3, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        grade_level_str, error = cls.get_field_value(row, 4)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        # Parse grade level
        try:
            grade_level = int(grade_level_str) if grade_level_str else None
        except ValueError:
            result['error'] = f'Line {line_num}: Invalid grade level, must be a number'
            return result
        
        # Construct full name
        name = f"{first_name} {last_name}"
        if nickname:
            name = f"{first_name} '{nickname}' {last_name}"
        
        # Create or update student
        try:
            student, created = Student.objects.update_or_create(
                id=student_id,
                defaults={
                    'name': name,
                    'grade_level': grade_level
                }
            )
            result['created'] = created
            result['updated'] = not created
            
        except Exception as e:
            result['error'] = f'Line {line_num}: Error processing student: {str(e)}'
            
        return result 