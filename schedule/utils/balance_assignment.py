"""
Utility functions for balancing student assignments across sections.
This module contains algorithms for optimally distributing students
between sections to achieve balanced class sizes.
"""
import random
from django.db import transaction
from django.db.models import Count, Q, F
from schedule.models import Student, Course, Section, CourseEnrollment, Enrollment, CourseGroup

def get_course_by_id(course_id):
    """Get a course by ID or return None"""
    try:
        return Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return None

def get_course_group(course):
    """Check if course is part of a course group"""
    return CourseGroup.objects.filter(courses=course).first()

def get_enrolled_students(course):
    """Get students enrolled in a course"""
    return CourseEnrollment.objects.filter(course=course).select_related('student')

def get_course_sections(course):
    """Get sections for a course"""
    return Section.objects.filter(course=course).select_related('period', 'teacher', 'room')

def student_has_period_conflict(student, period_id):
    """Check if student has an existing enrollment in the same period"""
    if not period_id:
        return False
    return Enrollment.objects.filter(
        student=student,
        section__period_id=period_id
    ).exists()

def assign_student_to_section(student, section):
    """Create an enrollment record for a student in a section"""
    return Enrollment.objects.create(student=student, section=section)

def handle_trimester_assignments(student_enrollment, course, section_data, assignments_count):
    """
    Special handling for trimester courses. Ensures students take each language
    course in a different trimester but same period.
    
    Returns: (updated_section_data, updated_assignment_count, success)
    """
    # Implementation details would go here
    # This is a placeholder for the complex trimester assignment logic
    return section_data, assignments_count, False

def handle_conflicts(student_enrollment, section_data):
    """
    Try to resolve schedule conflicts by finding alternative sections or
    by moving existing enrollments.
    
    Returns: (success, message)
    """
    # Implementation details would go here
    # This is a placeholder for the conflict resolution logic
    return False, "Unable to resolve conflict"

def perfect_balance_assignment(course_id=None):
    """
    Assign students to sections with optimal balancing.
    If course_id is provided, only assign for that course.
    Otherwise, assign for all courses.
    
    Returns dict with assignment results.
    """
    with transaction.atomic():
        unassigned_courses = []
        initial_assignments = 0
        initial_failures = 0
        conflicts_resolved = 0
        unresolvable_conflicts = 0
        errors = []
        
        # If course_id is specified, only process that course
        if course_id:
            course = get_course_by_id(course_id)
            if not course:
                return {
                    'status': 'error',
                    'message': f'Course with ID {course_id} not found',
                    'initial_assignments': 0,
                    'initial_failures': 0,
                    'conflicts_resolved': 0,
                    'unresolvable_conflicts': 0,
                    'errors': [f'Course with ID {course_id} not found']
                }
            courses = [course]
        else:
            # Process all courses with unassigned students
            courses = Course.objects.filter(
                student_enrollments__isnull=False
            ).distinct()
        
        # Process each course
        for course in courses:
            # Check if course is part of a group (like language courses across trimesters)
            course_group = get_course_group(course)
            is_grouped_course = course_group is not None
            
            # Get students enrolled in this course
            enrolled_students = get_enrolled_students(course)
            
            # Skip if no students enrolled
            if enrolled_students.count() == 0:
                continue
            
            # Get sections for this course
            sections = get_course_sections(course)
            
            # Skip if no sections available
            if sections.count() == 0:
                unassigned_courses.append(course.name)
                errors.append(f"No sections available for {course.name}")
                continue
            
            # Deregister all current section assignments for this course
            # This allows us to start fresh for optimal balancing
            current_enrollments = Enrollment.objects.filter(section__course=course)
            enrollment_count = current_enrollments.count()
            current_enrollments.delete()
            
            # Initialize section data
            section_data = []
            for section in sections:
                max_capacity = section.max_size if section.max_size else 999  # Use large value for "unlimited"
                section_data.append({
                    'section': section,
                    'current_enrollment': 0,
                    'max_capacity': max_capacity,
                    'period_id': section.period_id if section.period else None,
                    'when': section.when  # Add the when attribute for trimester/quarter scheduling
                })
            
            # Sort students by a stable criterion (ID) to ensure consistent assignments
            students_to_assign = list(enrolled_students)
            students_to_assign.sort(key=lambda e: e.student.id)
            
            # Special handling for grouped courses (trimester/quarter language courses)
            if is_grouped_course:
                # Handle special case for course groups
                # This would be implemented in the handle_trimester_assignments function
                pass
            
            # Track students with schedule conflicts for later resolution
            student_schedule_conflicts = []
            
            # First pass: assign students without conflicts
            assignments_count = 0
            for enrollment in students_to_assign:
                student = enrollment.student
                
                # Get current student schedule (periods they're already assigned to)
                student_periods = Enrollment.objects.filter(
                    student=student,
                    section__period__isnull=False
                ).values_list('section__period_id', flat=True)
                
                # Find eligible sections (no period conflicts)
                eligible_sections = []
                for section_info in section_data:
                    # Skip if student already has a class in this period
                    if section_info['period_id'] and section_info['period_id'] in student_periods:
                        continue
                    
                    # Skip sections at max capacity
                    if section_info['current_enrollment'] >= section_info['max_capacity']:
                        continue
                    
                    eligible_sections.append(section_info)
                
                if not eligible_sections:
                    # Save this student for conflict resolution
                    student_schedule_conflicts.append(enrollment)
                    continue
                
                # Find the section with lowest enrollment
                best_section = min(eligible_sections, key=lambda s: s['current_enrollment'])
                
                # Create enrollment record
                Enrollment.objects.create(
                    student=student,
                    section=best_section['section']
                )
                
                # Update section counts
                best_section['current_enrollment'] += 1
                assignments_count += 1
            
            # Handle students with schedule conflicts
            for enrollment in student_schedule_conflicts:
                student = enrollment.student
                # Attempt to resolve conflicts
                success, message = handle_conflicts(enrollment, section_data)
                if success:
                    conflicts_resolved += 1
                else:
                    unresolvable_conflicts += 1
                    
            # Update counters
            initial_assignments += assignments_count
            initial_failures += len(student_schedule_conflicts)
        
        # Return results
        return {
            'status': 'success',
            'message': f'Successfully assigned {initial_assignments} students to sections',
            'initial_assignments': initial_assignments,
            'initial_failures': initial_failures,
            'conflicts_resolved': conflicts_resolved,
            'unresolvable_conflicts': unresolvable_conflicts,
            'errors': errors
        } 