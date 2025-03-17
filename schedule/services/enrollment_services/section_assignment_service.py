from ...models import Student, Course, Section, Enrollment, CourseEnrollment
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q


class SectionAssignmentService:
    """Service class for assigning students to sections based on course enrollments."""
    
    @staticmethod
    def assign_students_to_sections(grade_level=None):
        """
        Assign students to sections based on course enrollments.
        Can be filtered by grade level.
        """
        # Get course enrollments that need section assignments
        course_enrollments = CourseEnrollment.objects.all()
        if grade_level:
            course_enrollments = course_enrollments.filter(student__grade_level=grade_level)
        
        # Group enrollments by course to process each course separately
        courses = Course.objects.filter(
            id__in=course_enrollments.values_list('course_id', flat=True).distinct()
        )
        
        total_assigned = 0
        total_failures = 0
        errors = []
        course_results = []
        
        with transaction.atomic():
            for course in courses:
                result = SectionAssignmentService.assign_course_sections(course, grade_level)
                course_results.append(result)
                total_assigned += result['assigned_count']
                total_failures += result['failure_count']
                errors.extend(result['errors'])
        
        return {
            'success': total_assigned > 0,
            'message': f"Assigned {total_assigned} students to sections, with {total_failures} failures",
            'total_assigned': total_assigned,
            'total_failures': total_failures,
            'errors': errors,
            'course_results': course_results
        }
    
    @staticmethod
    def assign_course_sections(course, grade_level=None):
        """Assign students to sections for a specific course."""
        # Get students enrolled in this course
        enrollments_query = CourseEnrollment.objects.filter(course=course)
        if grade_level:
            enrollments_query = enrollments_query.filter(student__grade_level=grade_level)
        
        enrollments = enrollments_query.select_related('student')
        
        # Get available sections for this course
        sections = Section.objects.filter(course=course).prefetch_related('enrollments')
        
        if not sections.exists():
            return {
                'course': course.name,
                'success': False,
                'message': f'No sections found for course {course.name}',
                'assigned_count': 0,
                'failure_count': enrollments.count(),
                'errors': [f'No sections found for course {course.name}']
            }
        
        # Calculate available capacity for each section
        section_capacities = {}
        for section in sections:
            enrolled_count = section.enrollments.count()
            max_size = section.max_size if section.max_size is not None else float('inf')
            section_capacities[section.id] = {
                'section': section,
                'enrolled': enrolled_count,
                'available': max_size - enrolled_count if max_size is not None else float('inf')
            }
        
        # Sort sections by available capacity (descending)
        sorted_sections = sorted(
            section_capacities.values(),
            key=lambda x: (float('-inf') if x['available'] == float('inf') else x['available']),
            reverse=True
        )
        
        assigned_count = 0
        failure_count = 0
        errors = []
        
        # Assign students to sections with available capacity
        for enrollment in enrollments:
            student = enrollment.student
            
            # Skip students who are already assigned to a section for this course
            if Enrollment.objects.filter(student=student, section__course=course).exists():
                continue
            
            # Try to find a section with available capacity
            assigned = False
            for section_data in sorted_sections:
                section = section_data['section']
                
                # Check if section has capacity
                if section_data['available'] <= 0:
                    continue
                
                # Check for period conflicts
                if section.period:
                    conflicts = Enrollment.objects.filter(
                        student=student,
                        section__period=section.period
                    ).exists()
                    
                    if conflicts:
                        continue
                
                # Assign student to this section
                Enrollment.objects.create(student=student, section=section)
                
                # Update section capacity
                section_data['enrolled'] += 1
                section_data['available'] -= 1
                
                assigned = True
                assigned_count += 1
                break
            
            if not assigned:
                failure_count += 1
                errors.append(f"Could not assign {student.name} to a section for {course.name}")
        
        return {
            'course': course.name,
            'success': assigned_count > 0,
            'message': f"Assigned {assigned_count} students to {course.name} sections, with {failure_count} failures",
            'assigned_count': assigned_count,
            'failure_count': failure_count,
            'errors': errors
        }
    
    @staticmethod
    def assign_student_to_course_section(student_id, course_id):
        """Assign a student to an available section for a specific course."""
        student = get_object_or_404(Student, pk=student_id)
        course = get_object_or_404(Course, pk=course_id)
        
        # Check if student is enrolled in the course
        if not CourseEnrollment.objects.filter(student=student, course=course).exists():
            return {
                'success': False,
                'message': f"Student {student.name} is not enrolled in {course.name}"
            }
        
        # Check if student is already assigned to a section for this course
        if Enrollment.objects.filter(student=student, section__course=course).exists():
            section = Enrollment.objects.filter(
                student=student, 
                section__course=course
            ).first().section
            
            return {
                'success': False,
                'message': f"Student {student.name} is already assigned to {course.name} section {section.section_number}"
            }
        
        # Get available sections for this course
        sections = Section.objects.filter(course=course)
        
        if not sections.exists():
            return {
                'success': False,
                'message': f"No sections found for course {course.name}"
            }
        
        # Find the best section for this student
        best_section = None
        for section in sections:
            # Check if section has capacity
            if section.max_size and section.enrollments.count() >= section.max_size:
                continue
            
            # Check for period conflicts
            if section.period:
                conflicts = Enrollment.objects.filter(
                    student=student,
                    section__period=section.period
                ).exists()
                
                if conflicts:
                    continue
            
            # If we get this far, this section works
            best_section = section
            break
        
        if not best_section:
            return {
                'success': False,
                'message': f"No available sections found for {student.name} in {course.name}"
            }
        
        # Assign student to the best section
        enrollment = Enrollment.objects.create(student=student, section=best_section)
        
        return {
            'success': True,
            'message': f"Assigned {student.name} to {course.name} section {best_section.section_number}",
            'enrollment': enrollment,
            'section': best_section
        } 