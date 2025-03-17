import csv
from django.http import HttpResponse
from ...models import Section, Period


class ExportService:
    """Service class for exporting section and schedule data."""
    
    @staticmethod
    def export_master_schedule():
        """Export the master schedule to a CSV file."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="master_schedule.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Period', 'Course', 'Teacher', 'Room', 'Students'])
        
        sections = Section.objects.all().select_related('period', 'course', 'teacher', 'room')
        
        # Group by period for better organization
        periods = Period.objects.all().order_by('start_time')
        
        for period in periods:
            period_sections = sections.filter(period=period)
            
            if not period_sections.exists():
                # Skip periods with no sections
                continue
            
            for section in period_sections:
                students_list = ", ".join([student.name for student in section.students.all()])
                writer.writerow([
                    period.period_name if period else "Unassigned",
                    section.course.name if section.course else "Unassigned",
                    section.teacher.name if section.teacher else "Unassigned",
                    section.room.number if section.room else "Unassigned",
                    students_list
                ])
            
            # Add a blank row between periods for readability
            writer.writerow([])
        
        return response
    
    @staticmethod
    def export_student_schedules(student=None):
        """
        Export student schedules to a CSV file.
        If student is provided, export only that student's schedule.
        Otherwise, export all student schedules.
        """
        response = HttpResponse(content_type='text/csv')
        
        if student:
            # Export a single student's schedule
            response['Content-Disposition'] = f'attachment; filename="{student.name}_schedule.csv"'
            writer = csv.writer(response)
            writer.writerow(['Student', 'Grade', 'Period', 'Course', 'Teacher', 'Room'])
            
            sections = student.sections.all().select_related('period', 'course', 'teacher', 'room')
            
            for section in sections:
                writer.writerow([
                    student.name,
                    student.grade_level,
                    section.period.period_name if section.period else "Unassigned",
                    section.course.name if section.course else "Unassigned",
                    section.teacher.name if section.teacher else "Unassigned",
                    section.room.number if section.room else "Unassigned"
                ])
        else:
            # Export all student schedules
            response['Content-Disposition'] = 'attachment; filename="all_student_schedules.csv"'
            writer = csv.writer(response)
            writer.writerow(['Student', 'Grade', 'Period', 'Course', 'Teacher', 'Room'])
            
            from ...models import Student
            students = Student.objects.all().prefetch_related(
                'sections__period', 'sections__course', 'sections__teacher', 'sections__room'
            )
            
            for student in students:
                sections = student.sections.all()
                
                if not sections.exists():
                    # Add a row for students with no sections
                    writer.writerow([student.name, student.grade_level, "No sections assigned", "", "", ""])
                    continue
                
                for section in sections:
                    writer.writerow([
                        student.name,
                        student.grade_level,
                        section.period.period_name if section.period else "Unassigned",
                        section.course.name if section.course else "Unassigned",
                        section.teacher.name if section.teacher else "Unassigned",
                        section.room.number if section.room else "Unassigned"
                    ])
                
                # Add a blank row between students for readability
                writer.writerow([])
        
        return response 