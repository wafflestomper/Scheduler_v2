from ...models import Student, Course, Section, Enrollment, CourseEnrollment
from django.db import transaction
from django.shortcuts import get_object_or_404
from ..enrollment_services.enrollment_service import EnrollmentService
from ..enrollment_services.course_enrollment_service import CourseEnrollmentService


class BatchOperationsService:
    """Service class for handling batch operations on enrollments."""
    
    @staticmethod
    def bulk_enroll_students_in_sections(student_ids, section_id):
        """Enroll multiple students in a section at once."""
        section = get_object_or_404(Section, pk=section_id)
        
        success_count = 0
        error_count = 0
        errors = []
        
        with transaction.atomic():
            for student_id in student_ids:
                try:
                    result = EnrollmentService.enroll_student_in_section(student_id, section_id)
                    if result['success']:
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(result['message'])
                except Exception as e:
                    error_count += 1
                    errors.append(f"Error processing student ID {student_id}: {str(e)}")
        
        return {
            'success': success_count > 0,
            'message': f"Enrolled {success_count} students in {section.course.name} section {section.section_number}",
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
    
    @staticmethod
    def clear_all_enrollments_for_students(student_ids):
        """Clear all section enrollments for multiple students."""
        success_count = 0
        error_count = 0
        errors = []
        
        for student_id in student_ids:
            try:
                result = EnrollmentService.clear_student_enrollments(student_id)
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(result['message'])
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing student ID {student_id}: {str(e)}")
        
        return {
            'success': success_count > 0,
            'message': f"Cleared enrollments for {success_count} students",
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
    
    @staticmethod
    def clear_all_course_enrollments_for_students(student_ids):
        """Clear all course enrollments for multiple students."""
        success_count = 0
        error_count = 0
        errors = []
        
        for student_id in student_ids:
            try:
                result = CourseEnrollmentService.clear_student_course_enrollments(student_id)
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(result['message'])
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing student ID {student_id}: {str(e)}")
        
        return {
            'success': success_count > 0,
            'message': f"Cleared course enrollments for {success_count} students",
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
    
    @staticmethod
    def enroll_grade_in_course(grade_level, course_id):
        """Enroll all students in a specific grade level in a course."""
        course = get_object_or_404(Course, pk=course_id)
        
        # Get all students in this grade level
        students = Student.objects.filter(grade_level=grade_level)
        
        success_count = 0
        error_count = 0
        errors = []
        
        with transaction.atomic():
            for student in students:
                try:
                    result = CourseEnrollmentService.enroll_student_in_course(student.id, course_id)
                    if result['success']:
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(result['message'])
                except Exception as e:
                    error_count += 1
                    errors.append(f"Error enrolling student {student.name}: {str(e)}")
        
        return {
            'success': success_count > 0,
            'message': f"Enrolled {success_count} grade {grade_level} students in {course.name}",
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
    
    @staticmethod
    def clear_section_enrollments_by_grade(section_id, grade_level):
        """Clear enrollments for a section, filtered by grade level."""
        section = get_object_or_404(Section, pk=section_id)
        
        # Get enrollments for this section and grade level
        enrollments = Enrollment.objects.filter(
            section=section, 
            student__grade_level=grade_level
        )
        
        count = enrollments.count()
        
        # Delete enrollments
        enrollments.delete()
        
        return {
            'success': True,
            'message': f"Cleared {count} enrollments for grade {grade_level} students in {section.course.name} section {section.section_number}",
            'count': count
        } 