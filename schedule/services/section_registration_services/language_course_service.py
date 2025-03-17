"""
Service class for handling language course registration operations.
"""
from django.db.models import Count
from django.db import transaction
from ...models import Student, Course, Period, Section, Enrollment, CourseEnrollment


class LanguageCourseService:
    """Service class for language course registration operations."""
    
    @staticmethod
    def assign_language_courses(student, language_courses=None, preferred_period=None):
        """
        Placeholder for language course assignment algorithm.
        
        Args:
            student: The Student object to assign
            language_courses: Optional list of Course objects (defaults to SPA6, CHI6, FRE6)
            preferred_period: Optional preferred Period object
            
        Returns:
            dict: Result with success flag, message, and assignments
        """
        student_name = student.name if hasattr(student, 'name') else str(student)
        
        return {
            'success': False,
            'message': f"Language course assignment temporarily unavailable: algorithm is being reimplemented for {student_name}",
            'assignments': []
        }
    
    @staticmethod
    def _find_valid_assignment(trimester_data, language_courses):
        """
        Placeholder for finding a valid assignment.
        
        Args:
            trimester_data: Dictionary of trimester -> course -> section
            language_courses: List of courses to assign
            
        Returns:
            None: Placeholder always returns None
        """
        return None
    
    @staticmethod
    def get_language_course_conflicts(student):
        """
        Check if a student has conflicts in their language course assignments.
        
        Args:
            student: The Student object to check
            
        Returns:
            list: List of conflict dictionaries with details
        """
        # Get language course assignments
        language_assignments = Enrollment.objects.filter(
            student=student,
            section__course__type='Language'
        ).select_related('section', 'section__course', 'section__period')
        
        if not language_assignments.exists():
            return []
        
        conflicts = []
        
        # Check if all are in the same period
        periods = set(a.section.period_id for a in language_assignments if a.section.period)
        if len(periods) > 1:
            periods_text = ", ".join(f"Period {p}" for p in periods)
            conflicts.append({
                'type': 'different_periods',
                'message': f"Language courses assigned to different periods: {periods_text}"
            })
        
        # Check if all are in different trimesters
        trimesters = {}
        for assignment in language_assignments:
            trimester = assignment.section.when
            if trimester in trimesters:
                conflicts.append({
                    'type': 'same_trimester',
                    'message': f"Multiple language courses assigned to {trimester}: {trimesters[trimester]} and {assignment.section.course.name}"
                })
            else:
                trimesters[trimester] = assignment.section.course.name
        
        return conflicts
    
    @staticmethod
    def balance_language_course_sections():
        """
        Placeholder for balancing language course sections.
        
        Returns:
            dict: Result with success flag, message, and stats
        """
        return {
            'success': False,
            'message': "Language course balancing temporarily unavailable: algorithm is being reimplemented",
            'changes_made': 0,
            'balanced_courses': 0
        } 