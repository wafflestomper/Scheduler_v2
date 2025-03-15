"""
Utility functions for section registration and assignment.
These functions help balance section enrollments and manage student assignments.
"""
import random
from django.db import transaction
from django.db.models import Count, Q, F
from schedule.models import Student, Course, Section, CourseEnrollment, Enrollment, CourseGroup

def get_section_stats(sections):
    """
    Calculate enrollment statistics for a list of sections.
    
    Args:
        sections: QuerySet of Section objects
        
    Returns:
        list: List of dictionaries with section stats
    """
    section_stats = []
    
    for section in sections:
        enrolled_count = section.students.count()
        remaining_capacity = section.max_size - enrolled_count if section.max_size else None
        
        section_stats.append({
            'section': section,
            'enrolled_count': enrolled_count,
            'capacity': section.max_size,
            'remaining_capacity': remaining_capacity
        })
    
    return section_stats

def get_course_enrollment_stats():
    """
    Get enrollment statistics for all courses.
    
    Returns:
        list: List of dictionaries with course enrollment stats
    """
    # Get counts by course
    course_enrollment_stats = CourseEnrollment.objects.values('course__id', 'course__name') \
        .annotate(
            total_enrolled=Count('student', distinct=True),
            assigned_to_sections=Count('student', distinct=True, filter=Q(student__sections__course=F('course')))
        ).order_by('course__name')
    
    # Calculate students needing assignment
    for stats in course_enrollment_stats:
        stats['needing_assignment'] = stats['total_enrolled'] - stats['assigned_to_sections']
    
    return course_enrollment_stats

def get_unassigned_students_count():
    """
    Get the count of students who have course enrollments but no section assignments.
    
    Returns:
        int: Count of unassigned students
    """
    # Get all course enrollments that don't have section assignments
    unassigned_enrollments = CourseEnrollment.objects.filter(
        ~Q(student__sections__course=F('course'))
    ).select_related('student', 'course')
    
    # Count unique students with unassigned enrollments
    return unassigned_enrollments.values('student').distinct().count()

def deregister_sections(course_id=None, grade_level=None):
    """
    Deregister student section assignments with optional filtering.
    
    Args:
        course_id: Optional course ID to filter by
        grade_level: Optional grade level to filter by
        
    Returns:
        int: Count of enrollments that were removed
    """
    with transaction.atomic():
        # Build the query based on filters
        query = Q()
        
        if course_id:
            query &= Q(section__course_id=course_id)
        
        if grade_level:
            query &= Q(student__grade_level=grade_level)
        
        # Count enrollments before deletion for reporting
        enrollment_count = Enrollment.objects.filter(query).count()
        
        # Delete the enrollments
        Enrollment.objects.filter(query).delete()
        
        return enrollment_count 