"""
Service class for handling section registration operations.
"""
from django.db.models import Count, Q, F
from django.db import transaction
from ...models import Student, Course, Section, CourseEnrollment, Enrollment


class RegistrationService:
    """Service class for section registration operations."""
    
    @staticmethod
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
            has_max_size = section.max_size is not None
            has_exact_size = section.exact_size is not None
            
            # Calculate remaining capacity based on max_size
            remaining_capacity = section.max_size - enrolled_count if has_max_size else None
            
            # Add statistics about exact_size
            exact_size_diff = None
            exact_size_status = None
            if has_exact_size:
                exact_size_diff = section.exact_size - enrolled_count
                if exact_size_diff > 0:
                    exact_size_status = 'under'
                elif exact_size_diff < 0:
                    exact_size_status = 'over'
                else:
                    exact_size_status = 'exact'
            
            section_stats.append({
                'section': section,
                'enrolled_count': enrolled_count,
                'capacity': section.max_size,
                'remaining_capacity': remaining_capacity,
                'exact_size': section.exact_size,
                'exact_size_diff': exact_size_diff,
                'exact_size_status': exact_size_status
            })
        
        return section_stats

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def deregister_sections(course_id=None, grade_level=None):
        """
        Deregister student section assignments with optional filtering.
        
        Args:
            course_id: Optional course ID to filter by
            grade_level: Optional grade level to filter by
            
        Returns:
            dict: Result with success flag, message, and count
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
            
            return {
                'success': True,
                'message': f"Successfully deregistered {enrollment_count} section assignments",
                'count': enrollment_count
            } 