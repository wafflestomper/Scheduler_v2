"""
Service class for handling scheduling algorithms.
"""
from django.db import transaction
from ...models import Student, Course, Section, Enrollment, CourseEnrollment


class AlgorithmService:
    """Service class for scheduling algorithms."""
    
    @staticmethod
    def balance_section_assignments(course_id=None):
        """
        Balance section assignments for enrolled students.
        
        Args:
            course_id: Optional course ID to filter by
            
        Returns:
            dict: Result with success flag, message, and stats
        """
        # Get course enrollments that need section assignments
        course_enrollments_query = CourseEnrollment.objects.all()
        if course_id:
            course_enrollments_query = course_enrollments_query.filter(course_id=course_id)
        
        # Group by course
        course_enrollments_by_course = {}
        for enrollment in course_enrollments_query.select_related('student', 'course'):
            if enrollment.course_id not in course_enrollments_by_course:
                course_enrollments_by_course[enrollment.course_id] = []
            course_enrollments_by_course[enrollment.course_id].append(enrollment)
        
        # Track results
        total_success = 0
        total_failure = 0
        course_results = []
        
        # Process each course
        with transaction.atomic():
            for course_id, enrollments in course_enrollments_by_course.items():
                result = AlgorithmService._balance_course_sections(course_id, enrollments)
                course_results.append(result)
                total_success += result['success_count']
                total_failure += result['failure_count']
        
        return {
            'success': total_success > 0,
            'message': f"Assigned {total_success} students to sections, with {total_failure} failures",
            'success_count': total_success,
            'failure_count': total_failure,
            'course_results': course_results
        }
    
    @staticmethod
    def _balance_course_sections(course_id, enrollments):
        """
        Balance section assignments for a specific course.
        
        Args:
            course_id: Course ID
            enrollments: List of CourseEnrollment objects
            
        Returns:
            dict: Result with success flag, message, and stats
        """
        # Get the course
        course = Course.objects.get(id=course_id)
        
        # Get sections for this course
        sections = Section.objects.filter(course_id=course_id).prefetch_related('students')
        
        if not sections.exists():
            return {
                'course': course.name,
                'success': False,
                'message': f"No sections found for course {course.name}",
                'success_count': 0,
                'failure_count': len(enrollments)
            }
        
        # Get section stats
        section_stats = []
        for section in sections:
            enrolled_count = section.students.count()
            capacity = float('inf') if section.max_size is None else section.max_size
            available = capacity - enrolled_count
            
            section_stats.append({
                'section': section,
                'enrolled_count': enrolled_count,
                'capacity': capacity,
                'available': available,
                'exact_size': section.exact_size
            })
        
        # Sort sections by available capacity (highest first)
        section_stats.sort(key=lambda s: float('-inf') if s['available'] == float('inf') else s['available'], reverse=True)
        
        # Track assignments
        success_count = 0
        failure_count = 0
        
        # Process each enrollment
        for enrollment in enrollments:
            student = enrollment.student
            
            # Skip if student is already in a section for this course
            if Enrollment.objects.filter(student=student, section__course_id=course_id).exists():
                continue
                
            # Try to assign to a section with capacity
            assigned = False
            
            for section_stat in section_stats:
                section = section_stat['section']
                
                # Skip if section is at capacity
                if section_stat['available'] <= 0:
                    continue
                
                # Check for period conflicts
                if section.period:
                    period_conflicts = Enrollment.objects.filter(
                        student=student,
                        section__period=section.period
                    ).exists()
                    
                    if period_conflicts:
                        continue
                
                # Assign student to this section
                Enrollment.objects.create(student=student, section=section)
                section_stat['enrolled_count'] += 1
                section_stat['available'] -= 1
                success_count += 1
                assigned = True
                break
            
            if not assigned:
                failure_count += 1
        
        # Re-sort sections for next assignment
        section_stats.sort(key=lambda s: float('-inf') if s['available'] == float('inf') else s['available'], reverse=True)
        
        return {
            'course': course.name,
            'success': success_count > 0,
            'message': f"Assigned {success_count} students to {course.name} sections, with {failure_count} failures",
            'success_count': success_count,
            'failure_count': failure_count
        }
    
    @staticmethod
    def register_language_and_core_courses(grade_level=6, undo_depth=3):
        """
        Register students for language and core courses.
        
        Args:
            grade_level: Grade level to process (default: 6)
            undo_depth: How many assignments to undo when conflicts occur
            
        Returns:
            dict: Result with success flag, message, and stats
        """
        # Get language courses
        language_courses = Course.objects.filter(
            type='Language',
            grade_level=grade_level
        )
        
        # Get core courses
        core_courses = Course.objects.filter(
            type='CORE',
            grade_level=grade_level
        )
        
        # Get students in this grade level
        students = Student.objects.filter(grade_level=grade_level)
        
        # Track results
        language_success = 0
        language_failure = 0
        core_success = 0
        core_failure = 0
        
        # Process language courses
        language_result = AlgorithmService._register_course_type(students, language_courses, undo_depth)
        language_success = language_result['success_count']
        language_failure = language_result['failure_count']
        
        # Process core courses
        core_result = AlgorithmService._register_course_type(students, core_courses, undo_depth)
        core_success = core_result['success_count']
        core_failure = core_result['failure_count']
        
        return {
            'success': (language_success + core_success) > 0,
            'message': f"Assigned {language_success + core_success} students to language and core courses, with {language_failure + core_failure} failures",
            'language_success': language_success,
            'language_failure': language_failure,
            'core_success': core_success,
            'core_failure': core_failure
        }
    
    @staticmethod
    def _register_course_type(students, courses, undo_depth):
        """
        Register students for a specific type of course.
        
        Args:
            students: QuerySet of Student objects
            courses: QuerySet of Course objects
            undo_depth: How many assignments to undo when conflicts occur
            
        Returns:
            dict: Result with success_count and failure_count
        """
        # TODO: Implement the algorithm logic
        # For now, return placeholder results
        return {
            'success_count': 0,
            'failure_count': 0
        } 