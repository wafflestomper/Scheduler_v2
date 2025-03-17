"""
Section CSV data processor
"""
from typing import List, Dict, Any
from ...models import Section, Course, Teacher, Period, Room
from .base_processor import BaseProcessor


class SectionProcessor(BaseProcessor):
    """Process CSV data for Section records"""
    
    @classmethod
    def get_expected_headers(cls) -> List[str]:
        """Return the expected CSV headers for section data"""
        return ['course', 'section_number', 'teacher', 'period', 'room', 'max_size', 'when']
    
    @classmethod
    def process_row(cls, row: List[str], line_num: int) -> Dict[str, Any]:
        """Process a single row of section data from CSV
        
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
            
        section_number, _ = cls.get_field_value(row, 1, default="1")
        teacher_id, _ = cls.get_field_value(row, 2)
        period_id, _ = cls.get_field_value(row, 3)
        room_id, _ = cls.get_field_value(row, 4)
        max_size_str, _ = cls.get_field_value(row, 5, default="30")
        when, _ = cls.get_field_value(row, 6, default="year")
        
        # Parse numeric values
        try:
            section_number_int = int(section_number) if section_number else 1
        except ValueError:
            result['error'] = f'Line {line_num}: Invalid section number, must be a number'
            return result
            
        try:
            max_size = int(max_size_str) if max_size_str else 30
        except ValueError:
            result['error'] = f'Line {line_num}: Invalid max size, must be a number'
            return result
        
        # Get related objects
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            result['error'] = f'Line {line_num}: Course with ID {course_id} does not exist'
            return result
        
        teacher = None
        if teacher_id:
            try:
                teacher = Teacher.objects.get(id=teacher_id)
            except Teacher.DoesNotExist:
                result['error'] = f'Line {line_num}: Teacher with ID {teacher_id} does not exist'
                return result
        
        period = None
        if period_id:
            try:
                period = Period.objects.get(id=period_id)
            except Period.DoesNotExist:
                result['error'] = f'Line {line_num}: Period with ID {period_id} does not exist'
                return result
                
        room = None
        if room_id:
            try:
                room = Room.objects.get(id=room_id)
            except Room.DoesNotExist:
                result['error'] = f'Line {line_num}: Room with ID {room_id} does not exist'
                return result
        
        # Generate a unique ID for the section
        section_id = f"{course_id}-{section_number}"
        
        # Create or update section
        try:
            section, created = Section.objects.update_or_create(
                id=section_id,
                defaults={
                    'course': course,
                    'section_number': section_number_int,
                    'teacher': teacher,
                    'period': period,
                    'room': room,
                    'max_size': max_size,
                    'when': when
                }
            )
            result['created'] = created
            result['updated'] = not created
            
        except Exception as e:
            result['error'] = f'Line {line_num}: Error processing section: {str(e)}'
            
        return result 