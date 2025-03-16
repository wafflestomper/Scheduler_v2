"""
Flexible algorithm for registering students into core and language classes.
This module implements an algorithm that prioritizes equal distribution across sections.
"""
from django.db import transaction
from schedule.models import Student, Course, Section, Enrollment

def register_students_to_sections(students, course_sections, undo_depth=3, max_iterations=None):
    """
    Register students to course sections prioritizing equal distribution of students.
    
    The algorithm works as follows:
    1. Assign students to the section with the most open seats
    2. If sections have equal open seats, prioritize the course with the least total seats
    3. If a student can't be placed, backtrack by undoing recent registrations and try alternatives
    
    Args:
        students: List of Student objects to register
        course_sections: Dictionary mapping course IDs to lists of Section objects
        undo_depth: Number of registrations to undo when backtracking (default: 3)
        max_iterations: Maximum number of iterations before giving up (defaults to number of students)
        
    Returns:
        tuple: (success, message, assignments)
            - success: Boolean indicating if all assignments were successful
            - message: Status message
            - assignments: List of created Enrollment objects
    """
    if max_iterations is None:
        max_iterations = len(students)
    
    # Initialize section enrollment counts
    section_data = {}
    for course_id, sections in course_sections.items():
        section_data[course_id] = []
        for section in sections:
            current_enrollment = Enrollment.objects.filter(section=section).count()
            section_data[course_id].append({
                'section': section,
                'current_enrollment': current_enrollment,
                'max_capacity': section.course.max_students,
                'open_seats': section.course.max_students - current_enrollment,
                'total_seats': section.course.max_students
            })
    
    # Track assignments for potential backtracking
    assignments = []
    assignment_history = []
    
    def get_most_open_section(course_id):
        """Get the section with the most open seats for a given course."""
        available_sections = [s for s in section_data[course_id] if s['open_seats'] > 0]
        if not available_sections:
            return None
        
        # Sort by open seats (descending), then by total seats (ascending)
        return sorted(available_sections, key=lambda s: (-s['open_seats'], s['total_seats']))[0]
    
    def register_student(student, course_id):
        """Register a student to the best available section for a course."""
        best_section = get_most_open_section(course_id)
        if not best_section:
            return None
        
        # Create enrollment
        enrollment = Enrollment.objects.create(student=student, section=best_section['section'])
        
        # Update section data
        best_section['current_enrollment'] += 1
        best_section['open_seats'] -= 1
        
        # Track for potential backtracking
        assignments.append(enrollment)
        assignment_history.append((student, course_id, best_section['section']))
        
        return enrollment
    
    def undo_registrations(count):
        """Undo the last 'count' registrations."""
        if not assignments:
            return
        
        for _ in range(min(count, len(assignments))):
            last_enrollment = assignments.pop()
            last_record = assignment_history.pop()
            student, course_id, section = last_record
            
            # Update section data
            for section_info in section_data[course_id]:
                if section_info['section'] == section:
                    section_info['current_enrollment'] -= 1
                    section_info['open_seats'] += 1
                    break
            
            # Delete enrollment
            last_enrollment.delete()
    
    with transaction.atomic():
        iteration_count = 0
        student_index = 0
        
        # Process each student
        while student_index < len(students) and iteration_count < max_iterations:
            student = students[student_index]
            success = True
            
            # Try to register student to each course
            for course_id in course_sections.keys():
                enrollment = register_student(student, course_id)
                
                if not enrollment:
                    # Failed to register, undo recent registrations and try alternatives
                    success = False
                    undo_registrations(undo_depth)
                    iteration_count += 1
                    break
            
            if success:
                # Successfully registered student to all courses, move to next student
                student_index += 1
            
            iteration_count += 1
    
    if student_index == len(students):
        return True, "Successfully registered all students", assignments
    else:
        return False, f"Failed to register all students. Completed {student_index}/{len(students)}", assignments

def register_language_and_core_courses(grade_level, undo_depth=3):
    """
    Register students to language and core courses for a specific grade level.
    
    Args:
        grade_level: The grade level to register (e.g., 6 for 6th grade)
        undo_depth: Number of registrations to undo when backtracking
        
    Returns:
        dict: Registration results with success and failure counts
    """
    # Get students for this grade level
    students = Student.objects.filter(grade_level=grade_level)
    
    # Get language courses for this grade level
    language_courses = Course.objects.filter(
        type='language',
        grade_level=grade_level
    )
    
    # Get core courses for this grade level
    core_courses = Course.objects.filter(
        type='core',
        grade_level=grade_level
    )
    
    # Combine all target courses
    target_courses = list(language_courses) + list(core_courses)
    
    # Get sections for these courses
    course_sections = {}
    for course in target_courses:
        sections = Section.objects.filter(course=course)
        if sections.exists():
            course_sections[course.id] = list(sections)
    
    # Check if we have all needed courses and sections
    if len(course_sections) < len(target_courses):
        missing_courses = [c.id for c in target_courses if c.id not in course_sections]
        return {
            'status': 'error',
            'message': f'Missing sections for courses: {", ".join(missing_courses)}',
            'language_success': 0,
            'language_failure': len(students),
            'core_success': 0,
            'core_failure': len(students)
        }
    
    # Register students to all courses
    success, message, assignments = register_students_to_sections(
        list(students),
        course_sections,
        undo_depth=undo_depth,
        max_iterations=len(students) * 10  # Allow more iterations for complex schedules
    )
    
    if success:
        return {
            'status': 'success',
            'message': 'Successfully registered all students to language and core courses',
            'language_success': len(students),
            'language_failure': 0,
            'core_success': len(students),
            'core_failure': 0
        }
    else:
        # Count successful registrations by course type
        language_success = 0
        core_success = 0
        
        # Get unique students with language course assignments
        language_students = set(Enrollment.objects.filter(
            section__course__in=language_courses,
            student__in=students
        ).values_list('student_id', flat=True))
        
        # Get unique students with core course assignments
        core_students = set(Enrollment.objects.filter(
            section__course__in=core_courses,
            student__in=students
        ).values_list('student_id', flat=True))
        
        language_success = len(language_students)
        core_success = len(core_students)
        
        return {
            'status': 'partial',
            'message': message,
            'language_success': language_success,
            'language_failure': len(students) - language_success,
            'core_success': core_success,
            'core_failure': len(students) - core_success
        } 