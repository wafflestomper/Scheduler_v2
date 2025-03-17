import csv
from io import StringIO
from django.http import HttpResponse


class TemplateService:
    """Service for generating CSV templates for different data types."""
    
    @staticmethod
    def get_template_csv(template_type):
        """Generate a template CSV file for a specific data type."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{template_type}_template.csv"'
        
        writer = csv.writer(response)
        
        if template_type == 'students':
            writer.writerow(['student_id', 'first_name', 'nickname', 'last_name', 'grade_level'])
            writer.writerow(['S001', 'John', '', 'Doe', '9'])
            writer.writerow(['S002', 'Jane', 'Jenny', 'Smith', '10'])
        
        elif template_type == 'teachers':
            writer.writerow(['teacher_id', 'first_name', 'last_name', 'availability', 'subjects'])
            writer.writerow(['T001', 'Robert', 'Johnson', 'full-time', 'Math, Science'])
            writer.writerow(['T002', 'Sarah', 'Williams', 'part-time', 'English, History'])
        
        elif template_type == 'rooms':
            writer.writerow(['room_id', 'number', 'capacity', 'type'])
            writer.writerow(['R001', 'Room 101', '30', 'classroom'])
            writer.writerow(['R002', 'Science Lab', '25', 'lab'])
        
        elif template_type == 'courses':
            writer.writerow(['course_id', 'name', 'course_type', 'eligible_teachers', 'grade_level', 'sections_needed', 'duration'])
            writer.writerow(['C001', 'Algebra I', 'core', 'T001|T002', '9', '2', 'year'])
            writer.writerow(['C002', 'Biology', 'elective', 'T003', '10', '3', 'trimester'])
        
        elif template_type == 'periods':
            writer.writerow(['period_id', 'period_name', 'days', 'slot', 'start_time', 'end_time'])
            writer.writerow(['P001', 'Period 1', 'MTWRF', '1', '08:00', '08:50'])
            writer.writerow(['P002', 'Period 2', 'MTWRF', '2', '09:00', '09:50'])
        
        elif template_type == 'sections':
            writer.writerow(['course', 'section_number', 'teacher', 'period', 'room', 'max_size', 'when'])
            writer.writerow(['C001', '1', 'T001', 'P001', 'R001', '25', 'year'])
            writer.writerow(['C002', '2', '', 'P002', '', '30', 'trimester'])  # Example with optional fields blank
        
        else:
            return HttpResponse(f"Unknown template type: {template_type}", status=400)
        
        return response 