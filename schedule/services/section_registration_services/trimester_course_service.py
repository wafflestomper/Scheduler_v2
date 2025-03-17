"""
Service class for handling trimester course registration operations.
"""
from django.db.models import Count
from django.db import transaction
from ...models import Student, Course, Period, Section, Enrollment, CourseEnrollment, TrimesterCourseGroup


class TrimesterCourseService:
    """Service class for trimester course registration operations."""
    
    @staticmethod
    def assign_trimester_courses(student, group_ids, preferred_period=None):
        """
        Placeholder for assigning a student to trimester courses.
        
        Args:
            student: The Student object to assign
            group_ids: List of trimester course group IDs
            preferred_period: Optional preferred Period object
            
        Returns:
            dict: Result with success flag, message, and assignments
        """
        student_name = student.name if hasattr(student, 'name') else str(student)
        
        return {
            'success': False,
            'message': f"Trimester course assignment temporarily unavailable: algorithm is being reimplemented for {student_name}",
            'assignments': []
        }
    
    @staticmethod
    def _find_valid_assignment(trimesters, groups):
        """
        Placeholder for finding a valid assignment.
        
        Args:
            trimesters: Dictionary of trimester -> group_id -> sections
            groups: List of TrimesterCourseGroup objects
            
        Returns:
            None: Placeholder always returns None
        """
        return None
    
    @staticmethod
    def get_trimester_course_conflicts(student):
        """
        Check if a student has conflicts in their trimester course assignments.
        
        Args:
            student: The Student object to check
            
        Returns:
            list: List of conflict dictionaries with details
        """
        # Get all trimester groups and their courses
        trimester_groups = TrimesterCourseGroup.objects.all().prefetch_related('courses')
        
        # Create a map of course IDs to group IDs
        course_to_group = {}
        for group in trimester_groups:
            for course in group.courses.all():
                course_to_group[course.id] = group.id
        
        # Get all trimester course assignments
        trimester_assignments = Enrollment.objects.filter(
            student=student,
            section__course__id__in=course_to_group.keys()
        ).select_related('section', 'section__course', 'section__period')
        
        if not trimester_assignments.exists():
            return []
        
        conflicts = []
        
        # Check if all courses from the same group are assigned
        assignments_by_group = {}
        for assignment in trimester_assignments:
            course_id = assignment.section.course_id
            group_id = course_to_group.get(course_id)
            
            if group_id not in assignments_by_group:
                assignments_by_group[group_id] = []
                
            assignments_by_group[group_id].append(assignment)
        
        # Check if multiple courses from the same group are assigned
        for group_id, assignments in assignments_by_group.items():
            if len(assignments) > 1:
                course_names = [a.section.course.name for a in assignments]
                conflicts.append({
                    'type': 'multiple_courses_same_group',
                    'message': f"Multiple courses from the same group {group_id} assigned: {', '.join(course_names)}"
                })
        
        # Check if all assignments have the same period
        periods = set(a.section.period_id for a in trimester_assignments if a.section.period)
        if len(periods) > 1:
            conflicts.append({
                'type': 'different_periods',
                'message': f"Trimester courses assigned to different periods: {', '.join(f'Period {p}' for p in periods)}"
            })
        
        return conflicts
    
    @staticmethod
    def balance_trimester_courses():
        """
        Placeholder for balancing trimester courses.
        
        Returns:
            dict: Result with success flag and message
        """
        return {
            'success': False,
            'message': "Trimester course balancing temporarily unavailable: algorithm is being reimplemented",
            'balanced_sections': 0,
            'unbalanced_sections': 0
        }
    
    @staticmethod
    def _balance_sections(section_enrollments, target_size):
        """
        Placeholder for balancing sections.
        
        Args:
            section_enrollments: List of section enrollments
            target_size: Target section size
            
        Returns:
            dict: Result with success flag and message
        """
        return {
            'success': False,
            'message': "Section balancing temporarily unavailable: algorithm is being reimplemented",
            'moved_enrollments': []
        } 