"""
Flexible algorithm for registering students into core and language classes.
This module implements an algorithm that prioritizes equal distribution across sections.
"""
from django.db import transaction
from schedule.models import Student, Course, Section, Enrollment, CourseEnrollment
import logging

# Set up logging
logger = logging.getLogger(__name__)

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
    print(f"DEBUG: Starting registration for {len(students)} students")
    print(f"DEBUG: Course sections: {', '.join([f'{c_id}({len(secs)})' for c_id, secs in course_sections.items()])}")
    
    if max_iterations is None:
        max_iterations = len(students)
    
    # Initialize section enrollment counts
    section_data = {}
    for course_id, sections in course_sections.items():
        section_data[course_id] = []
        print(f"DEBUG: Processing course {course_id} with {len(sections)} sections")
        for section in sections:
            current_enrollment = Enrollment.objects.filter(section=section).count()
            # Use default max_size of 25 if not set
            max_size = section.max_size if section.max_size is not None else 25
            section_data[course_id].append({
                'section': section,
                'current_enrollment': current_enrollment,
                'max_capacity': max_size,
                'open_seats': max_size - current_enrollment,
                'total_seats': max_size
            })
            print(f"DEBUG: Section {section.id} has {current_enrollment}/{max_size} students")
    
    # Track assignments for potential backtracking
    assignments = []
    assignment_history = []
    
    def get_most_open_section(course_id):
        """Get the section with the most open seats for a given course."""
        available_sections = [s for s in section_data[course_id] if s['open_seats'] > 0]
        if not available_sections:
            print(f"DEBUG: No available sections for course {course_id}")
            return None
        
        # Sort by open seats (descending), then by total seats (ascending)
        return sorted(available_sections, key=lambda s: (-s['open_seats'], s['total_seats']))[0]
    
    def register_student(student, course_id):
        """Register a student to the best available section for a course."""
        best_section = get_most_open_section(course_id)
        if not best_section:
            print(f"DEBUG: Failed to find section for student {student.id} in course {course_id}")
            return None
        
        # Create enrollment
        enrollment = Enrollment.objects.create(student=student, section=best_section['section'])
        print(f"DEBUG: Registered student {student.id} to section {best_section['section'].id} of course {course_id}")
        
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
            print("DEBUG: No assignments to undo")
            return
        
        print(f"DEBUG: Undoing {min(count, len(assignments))} registrations")
        for _ in range(min(count, len(assignments))):
            last_enrollment = assignments.pop()
            last_record = assignment_history.pop()
            student, course_id, section = last_record
            
            print(f"DEBUG: Undoing registration of student {student.id} in section {section.id}")
            
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
            
            print(f"DEBUG: Processing student {student.id} ({student_index + 1}/{len(students)})")
            
            # Try to register student to each course
            for course_id in course_sections.keys():
                enrollment = register_student(student, course_id)
                
                if not enrollment:
                    # Failed to register, undo recent registrations and try alternatives
                    success = False
                    print(f"DEBUG: Failed to register student {student.id} to course {course_id}, backtracking...")
                    undo_registrations(undo_depth)
                    iteration_count += 1
                    break
            
            if success:
                # Successfully registered student to all courses, move to next student
                print(f"DEBUG: Successfully registered student {student.id} to all courses")
                student_index += 1
            
            iteration_count += 1
            if iteration_count % 10 == 0:
                print(f"DEBUG: Iteration {iteration_count}, processed {student_index}/{len(students)} students")
    
    print(f"DEBUG: Completed with {student_index}/{len(students)} students successfully registered")
    if student_index == len(students):
        return True, f"Successfully registered all {len(students)} students", assignments
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
    print(f"DEBUG: Starting language and core course registration for grade {grade_level}")
    
    # Get students for this grade level
    students = Student.objects.filter(grade_level=grade_level)
    print(f"DEBUG: Found {students.count()} students in grade {grade_level}")
    
    if students.count() == 0:
        print(f"DEBUG: No students found for grade {grade_level}")
        return {
            'status': 'error',
            'message': f'No students found for grade {grade_level}',
            'language_success': 0,
            'language_failure': 0,
            'core_success': 0,
            'core_failure': 0
        }
    
    # Get language courses for this grade level - update type to match database
    language_courses = Course.objects.filter(
        type='Language',  # Changed from 'language' to 'Language'
        grade_level=grade_level
    )
    print(f"DEBUG: Found {language_courses.count()} language courses for grade {grade_level}")
    
    # Get core courses for this grade level - update type to match database
    core_courses = Course.objects.filter(
        type='CORE',  # Changed from 'core' to 'CORE'
        grade_level=grade_level
    )
    print(f"DEBUG: Found {core_courses.count()} core courses for grade {grade_level}")
    
    # Combine all target courses
    target_courses = list(language_courses) + list(core_courses)
    
    if not target_courses:
        print(f"DEBUG: No courses found for grade {grade_level}")
        return {
            'status': 'error',
            'message': f'No courses found for grade {grade_level}',
            'language_success': 0,
            'language_failure': 0,
            'core_success': 0,
            'core_failure': 0
        }
    
    # Get sections for these courses
    course_sections = {}
    for course in target_courses:
        sections = Section.objects.filter(course=course)
        if sections.exists():
            course_sections[course.id] = list(sections)
            print(f"DEBUG: Found {sections.count()} sections for course {course.id}")
        else:
            print(f"DEBUG: No sections found for course {course.id}")
    
    # Check if we have all needed courses and sections
    if len(course_sections) < len(target_courses):
        missing_courses = [c.id for c in target_courses if c.id not in course_sections]
        print(f"DEBUG: Missing sections for courses: {', '.join(missing_courses)}")
        return {
            'status': 'error',
            'message': f'Missing sections for courses: {", ".join(missing_courses)}',
            'language_success': 0,
            'language_failure': len(students),
            'core_success': 0,
            'core_failure': len(students)
        }
    
    # Check if students are already enrolled in these courses
    course_ids = [course.id for course in target_courses]
    student_course_enrollments = {}
    
    for student in students:
        student_course_enrollments[student.id] = set()
        
    # Get existing course enrollments
    existing_enrollments = CourseEnrollment.objects.filter(
        student__in=students,
        course__id__in=course_ids
    )
    
    # Count existing enrollments
    for enrollment in existing_enrollments:
        student_course_enrollments[enrollment.student_id].add(enrollment.course_id)
    
    # Create missing course enrollments
    for student in students:
        for course in target_courses:
            if course.id not in student_course_enrollments[student.id]:
                print(f"DEBUG: Creating course enrollment for student {student.id} in course {course.id}")
                CourseEnrollment.objects.create(student=student, course=course)
    
    # Register students to all courses
    print(f"DEBUG: Starting registration algorithm for {len(students)} students and {len(course_sections)} courses")
    success, message, assignments = register_students_to_sections(
        list(students),
        course_sections,
        undo_depth=undo_depth,
        max_iterations=len(students) * 10  # Allow more iterations for complex schedules
    )
    
    if success:
        print(f"DEBUG: Registration successful for all {len(students)} students")
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
        print(f"DEBUG: Partial success, counting successful registrations")
        language_success = 0
        core_success = 0
        
        # Get unique students with language course assignments - update type to match database
        language_students = set(Enrollment.objects.filter(
            section__course__in=language_courses,
            student__in=students
        ).values_list('student_id', flat=True))
        
        # Get unique students with core course assignments - update type to match database
        core_students = set(Enrollment.objects.filter(
            section__course__in=core_courses,
            student__in=students
        ).values_list('student_id', flat=True))
        
        language_success = len(language_students)
        core_success = len(core_students)
        
        print(f"DEBUG: Language success: {language_success}/{len(students)}")
        print(f"DEBUG: Core success: {core_success}/{len(students)}")
        
        return {
            'status': 'partial',
            'message': message,
            'language_success': language_success,
            'language_failure': len(students) - language_success,
            'core_success': core_success,
            'core_failure': len(students) - core_success
        }