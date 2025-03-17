from ...models import Student, Course, CourseEnrollment
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q


class CourseEnrollmentService:
    """Service class for handling course enrollment operations."""
    
    @staticmethod
    def get_student_course_enrollments(student_id):
        """Get all course enrollments for a student."""
        student = get_object_or_404(Student, pk=student_id)
        enrollments = CourseEnrollment.objects.filter(student=student).select_related('course')
        
        return {
            'student': student,
            'enrollments': enrollments,
            'count': enrollments.count()
        }
    
    @staticmethod
    def get_course_enrollments(course_id):
        """Get all student enrollments for a course."""
        course = get_object_or_404(Course, pk=course_id)
        enrollments = CourseEnrollment.objects.filter(course=course).select_related('student')
        
        return {
            'course': course,
            'enrollments': enrollments,
            'count': enrollments.count()
        }
    
    @staticmethod
    def enroll_student_in_course(student_id, course_id):
        """Enroll a student in a course."""
        student = get_object_or_404(Student, pk=student_id)
        course = get_object_or_404(Course, pk=course_id)
        
        # Check if already enrolled
        if CourseEnrollment.objects.filter(student=student, course=course).exists():
            return {
                'success': False,
                'message': f"Student {student.name} is already enrolled in {course.name}"
            }
        
        # Enroll the student
        enrollment = CourseEnrollment.objects.create(student=student, course=course)
        
        return {
            'success': True,
            'message': f"Student {student.name} enrolled in {course.name}",
            'enrollment': enrollment
        }
    
    @staticmethod
    def remove_student_from_course(student_id, course_id):
        """Remove a student from a course."""
        student = get_object_or_404(Student, pk=student_id)
        course = get_object_or_404(Course, pk=course_id)
        
        # Check if enrolled
        enrollment = CourseEnrollment.objects.filter(student=student, course=course).first()
        if not enrollment:
            return {
                'success': False,
                'message': f"Student {student.name} is not enrolled in {course.name}"
            }
        
        # Remove enrollment
        enrollment.delete()
        
        return {
            'success': True,
            'message': f"Student {student.name} removed from {course.name}"
        }
    
    @staticmethod
    def clear_student_course_enrollments(student_id):
        """Clear all course enrollments for a student."""
        student = get_object_or_404(Student, pk=student_id)
        
        # Count enrollments before deletion
        enrollment_count = CourseEnrollment.objects.filter(student=student).count()
        
        # Delete all enrollments
        CourseEnrollment.objects.filter(student=student).delete()
        
        return {
            'success': True,
            'message': f"Cleared {enrollment_count} course enrollments for {student.name}",
            'count': enrollment_count
        }
    
    @staticmethod
    def clear_course_enrollments(course_id):
        """Clear all student enrollments for a course."""
        course = get_object_or_404(Course, pk=course_id)
        
        # Count enrollments before deletion
        enrollment_count = CourseEnrollment.objects.filter(course=course).count()
        
        # Delete all enrollments
        CourseEnrollment.objects.filter(course=course).delete()
        
        return {
            'success': True,
            'message': f"Cleared {enrollment_count} student enrollments for {course.name}",
            'count': enrollment_count
        }
    
    @staticmethod
    def bulk_enroll_students_in_course(student_ids, course_id):
        """Enroll multiple students in a course."""
        course = get_object_or_404(Course, pk=course_id)
        
        success_count = 0
        error_count = 0
        errors = []
        
        with transaction.atomic():
            for student_id in student_ids:
                try:
                    student = Student.objects.get(pk=student_id)
                    
                    # Skip if already enrolled
                    if CourseEnrollment.objects.filter(student=student, course=course).exists():
                        error_count += 1
                        errors.append(f"Student {student.name} is already enrolled in {course.name}")
                        continue
                    
                    # Enroll the student
                    CourseEnrollment.objects.create(student=student, course=course)
                    success_count += 1
                    
                except Student.DoesNotExist:
                    error_count += 1
                    errors.append(f"Student ID {student_id} not found")
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Error enrolling student {student_id}: {str(e)}")
        
        return {
            'success': success_count > 0,
            'message': f"Enrolled {success_count} students in {course.name}",
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
    
    @staticmethod
    def get_enrolled_students_with_counts(grade_filter=None, course_ids=None):
        """Get students with their enrollment counts, optionally filtered by grade and/or courses."""
        # Base queryset for students
        students = Student.objects.all().order_by('name')
        
        # Filter students by grade if specified
        if grade_filter:
            students = students.filter(grade_level=grade_filter)
        
        # Get selected courses if specified
        selected_courses = []
        if course_ids:
            selected_courses = Course.objects.filter(id__in=course_ids)
        
        # Prepare student data with enrollment info
        student_data = []
        for student in students:
            # Count course enrollments
            enrolled_course_count = CourseEnrollment.objects.filter(student=student).count()
            
            # Count section registrations (actual section assignments)
            registered_section_count = student.sections.count()
            
            # Check if student is enrolled in the selected courses
            enrolled_in_selected_course = False
            if selected_courses:
                # Check if enrolled in ANY of the selected courses
                enrolled_in_selected_course = CourseEnrollment.objects.filter(
                    student=student,
                    course__in=selected_courses
                ).exists()
            elif grade_filter:
                # If "All Courses" is selected with a grade filter, 
                # mark students as "enrolled" if they have any course enrollments
                enrolled_in_selected_course = enrolled_course_count > 0
            
            student_data.append({
                'student': student,
                'enrolled_course_count': enrolled_course_count,
                'registered_section_count': registered_section_count,
                'enrolled_in_selected_course': enrolled_in_selected_course
            })
        
        return {
            'students': student_data,
            'total_count': len(student_data)
        } 