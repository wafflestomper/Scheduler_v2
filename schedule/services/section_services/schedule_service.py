from django.db.models import Count
from ...models import Section, Student, Period


class ScheduleService:
    """Service class for managing schedule displays and organization."""
    
    @staticmethod
    def get_master_schedule():
        """Get the master schedule organized by period and day."""
        # Get all sections
        sections = Section.objects.select_related('period', 'course', 'teacher', 'room').exclude(period__isnull=True)
        
        # Group by period
        schedule = {}
        for section in sections:
            period_id = section.period.id
            if period_id not in schedule:
                schedule[period_id] = {
                    'period': section.period,
                    'sections': []
                }
            
            schedule[period_id]['sections'].append(section)
        
        # Sort periods by slot
        sorted_schedule = {}
        periods = Period.objects.all().order_by('slot')
        for period in periods:
            if period.id in schedule:
                sorted_schedule[period.id] = schedule[period.id]
        
        # Get statistics on the schedule
        unassigned_sections = Section.objects.filter(period__isnull=True).count()
        
        return {
            'schedule': sorted_schedule,
            'total_sections': sections.count(),
            'unassigned_sections': unassigned_sections
        }
    
    @staticmethod
    def get_student_schedule(student_id):
        """Get a specific student's schedule organized by period."""
        # Get the student
        student = Student.objects.get(pk=student_id)
        
        # Get all sections the student is enrolled in
        sections = student.sections.select_related('period', 'course', 'teacher', 'room')
        
        # Group by period
        schedule = {}
        for section in sections:
            if not section.period:
                continue
            
            period_id = section.period.id
            if period_id not in schedule:
                schedule[period_id] = {
                    'period': section.period,
                    'sections': []
                }
            
            schedule[period_id]['sections'].append(section)
        
        # Sort periods by time
        sorted_schedule = {}
        for period_id in sorted(schedule.keys()):
            sorted_schedule[period_id] = schedule[period_id]
        
        return {
            'student': student,
            'schedule': sorted_schedule,
            'section_count': sections.count()
        }
    
    @staticmethod
    def get_all_student_schedules_summary():
        """Get a summary of all students with their section counts."""
        # List all students with their section counts
        students = Student.objects.all().order_by('name')
        
        # Get counts of sections for each student
        students_with_counts = []
        for student in students:
            section_count = student.sections.count()
            students_with_counts.append({
                'student': student,
                'section_count': section_count
            })
        
        return {
            'students_with_counts': students_with_counts,
            'total_students': len(students_with_counts)
        } 