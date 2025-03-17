"""
Course CSV data processor
"""
from typing import List, Dict, Any
from ...models import Course
from .base_processor import BaseProcessor


class CourseProcessor(BaseProcessor):
    """Process CSV data for Course records"""
    
    @classmethod
    def get_expected_headers(cls) -> List[str]:
        """Return the expected CSV headers for course data"""
        return ['course_id', 'name', 'course_type', 'eligible_teachers', 'grade_level', 'sections_needed', 'duration']
    
    @classmethod
    def process_row(cls, row: List[str], line_num: int) -> Dict[str, Any]:
        """Process a single row of course data from CSV
        
        Args:
            row: The CSV row as a list of strings
            line_num: The line number in the CSV file (for error reporting)
            
        Returns:
            Dictionary with processing results and any errors
        """
        result = {'created': False, 'updated': False, 'error': None}
        
        # Get field values with validation
        course_id, error = cls.get_field_value(row, 0, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        name, error = cls.get_field_value(row, 1, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        course_type, error = cls.get_field_value(row, 2, required=True)
        if error:
            result['error'] = f'Line {line_num}: {error}'
            return result
            
        eligible_teachers, _ = cls.get_field_value(row, 3, default="")
        
        grade_level_str, _ = cls.get_field_value(row, 4, default="0")
        sections_needed_str, _ = cls.get_field_value(row, 5, default="1")
        duration, _ = cls.get_field_value(row, 6, default="year")
        
        # Parse numeric values
        try:
            grade_level = int(grade_level_str) if grade_level_str else 0
        except ValueError:
            result['error'] = f'Line {line_num}: Invalid grade level, must be a number'
            return result
            
        try:
            sections_needed = int(sections_needed_str) if sections_needed_str else 1
        except ValueError:
            result['error'] = f'Line {line_num}: Invalid sections needed, must be a number'
            return result
        
        # Create or update course
        try:
            course, created = Course.objects.update_or_create(
                id=course_id,
                defaults={
                    'name': name,
                    'type': course_type,
                    'eligible_teachers': eligible_teachers,
                    'grade_level': grade_level,
                    'sections_needed': sections_needed,
                    'duration': duration
                }
            )
            result['created'] = created
            result['updated'] = not created
            
        except Exception as e:
            result['error'] = f'Line {line_num}: Error processing course: {str(e)}'
            
        return result 