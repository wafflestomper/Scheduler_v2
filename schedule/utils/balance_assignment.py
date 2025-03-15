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
    # Delegate to unified_assignment algorithm
    return unified_assignment(course_id)

def unified_assignment(course_id=None):
    """
    Unified algorithm for assigning all types of courses:
    - Regular courses
    - Language courses (requiring different trimesters but same period)
    - Trimester electives (one from each group in different trimesters but same period)
    
    This algorithm follows a priority order:
    1. First pass: Process specialty courses (language and trimester groups)
    2. Second pass: Process regular courses
    
    If course_id is provided, only assign for that course.
    Otherwise, assign for all courses.
    
    Returns dict with assignment results.
    """
    from schedule.utils.language_course_utils import assign_language_courses
    from schedule.utils.trimester_course_utils import assign_trimester_courses
    from schedule.models import TrimesterCourseGroup, CourseGroup
    
    with transaction.atomic():
        unassigned_courses = []
        initial_assignments = 0
        initial_failures = 0
        conflicts_resolved = 0
        unresolvable_conflicts = 0
        errors = []
        
        # Track stats for each course type
        language_assignments = 0
        language_failures = 0
        trimester_assignments = 0
        trimester_failures = 0
        regular_assignments = 0
        regular_failures = 0
        
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
            
            # Check if it's a language course
            is_language_course = (course.type == 'language')
            
            # Check if it's a trimester course
            is_trimester_course = TrimesterCourseGroup.objects.filter(courses=course).exists()
            
            if is_language_course:
                # Handle language course assignment
                return handle_language_course_assignment(course)
            elif is_trimester_course:
                # Handle trimester course assignment
                return handle_trimester_course_assignment(course)
            else:
                # Process regular course
                courses = [course]
        else:
            # PHASE 1: Process special course types
            
            # Process language courses (all 6th grade students)
            language_stats = process_language_courses()
            language_assignments = language_stats['assignments']
            language_failures = language_stats['failures']
            
            # Process trimester courses (all 6th grade students)
            trimester_stats = process_trimester_courses()
            trimester_assignments = trimester_stats['assignments']
            trimester_failures = trimester_stats['failures']
            
            # PHASE 2: Process regular courses
            # Only process courses not handled in the special phases
            
            # Get language course IDs
            language_course_ids = Course.objects.filter(type='language').values_list('id', flat=True)
            
            # Get trimester course IDs
            trimester_group_courses = []
            for group in TrimesterCourseGroup.objects.all():
                trimester_group_courses.extend(group.courses.values_list('id', flat=True))
            
            # Get all courses with unassigned students, excluding special types
            courses = Course.objects.filter(
                student_enrollments__isnull=False
            ).exclude(
                id__in=list(language_course_ids) + list(trimester_group_courses)
            ).distinct()
        
        # Process each regular course
        for course in courses:
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
                    'when': section.when  # For trimester/quarter scheduling
                })
            
            # Sort students by a stable criterion (ID) to ensure consistent assignments
            students_to_assign = list(enrolled_students)
            students_to_assign.sort(key=lambda e: e.student.id)
            
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
            
            # Update regular course counters
            regular_assignments += assignments_count
            regular_failures += len(student_schedule_conflicts)
        
        # Update overall counters
        initial_assignments = regular_assignments + language_assignments + trimester_assignments
        initial_failures = regular_failures + language_failures + trimester_failures
        
        # Return results
        return {
            'status': 'success',
            'message': f'Successfully assigned {initial_assignments} students to sections',
            'initial_assignments': initial_assignments,
            'initial_failures': initial_failures,
            'conflicts_resolved': conflicts_resolved,
            'unresolvable_conflicts': unresolvable_conflicts,
            'errors': errors,
            'language_assignments': language_assignments,
            'language_failures': language_failures,
            'trimester_assignments': trimester_assignments,
            'trimester_failures': trimester_failures,
            'regular_assignments': regular_assignments,
            'regular_failures': regular_failures
        }

def process_language_courses():
    """
    Process all language course enrollments for all students.
    Returns statistics about assignments made.
    """
    from schedule.utils.language_course_utils import assign_language_courses
    
    assignments_count = 0
    failures_count = 0
    
    # Get language courses for 6th grade
    language_courses = Course.objects.filter(
        type='language', 
        grade_level=6
    )
    
    # Get students enrolled in language courses
    students = Student.objects.filter(
        course_enrollments__course__in=language_courses
    ).distinct()
    
    print(f"Processing language courses for {students.count()} students")
    
    # Remove existing language course assignments
    Enrollment.objects.filter(
        student__in=students,
        section__course__in=language_courses
    ).delete()
    
    # Process each student
    for student in students:
        # Get student's language course enrollments
        enrolled_courses = Course.objects.filter(
            student_enrollments__student=student,
            type='language'
        )
        
        # Skip if no language course enrollments
        if enrolled_courses.count() == 0:
            continue
        
        # Try to assign language courses
        success, message, assignments = assign_language_courses(student, enrolled_courses.all())
        
        if success:
            assignments_count += len(assignments)
        else:
            failures_count += 1
    
    return {
        'assignments': assignments_count,
        'failures': failures_count
    }

def process_trimester_courses():
    """
    Process all trimester course enrollments for all students.
    Returns statistics about assignments made.
    """
    from schedule.utils.trimester_course_utils import assign_trimester_courses
    from schedule.models import TrimesterCourseGroup
    
    assignments_count = 0
    failures_count = 0
    
    # Get all trimester course groups
    trimester_groups = TrimesterCourseGroup.objects.all().prefetch_related('courses')
    
    # Get all courses in these groups
    all_trimester_courses = []
    for group in trimester_groups:
        all_trimester_courses.extend(list(group.courses.all()))
    
    # Get group IDs for all trimester groups
    group_ids = list(trimester_groups.values_list('id', flat=True))
    
    # Get ALL 6th grade students - we want to check if they're enrolled in ANY trimester course
    all_6th_grade_students = Student.objects.filter(grade_level=6)
    
    print(f"Checking {all_6th_grade_students.count()} 6th grade students for trimester course enrollments")
    
    students_processed = 0
    
    # Process each 6th grade student
    for student in all_6th_grade_students:
        # Get this student's enrollment in trimester courses
        student_course_enrollments = CourseEnrollment.objects.filter(
            student=student,
            course__in=all_trimester_courses
        )
        
        # Skip if not enrolled in any trimester courses
        if not student_course_enrollments.exists():
            continue
        
        # Check if student has enrollments in at least one course from each group
        has_all_required_groups = True
        for group in trimester_groups:
            # Check if student is enrolled in any course from this group
            enrolled_in_group = CourseEnrollment.objects.filter(
                student=student,
                course__in=group.courses.all()
            ).exists()
            
            if not enrolled_in_group:
                has_all_required_groups = False
                break
        
        if not has_all_required_groups:
            print(f"Student {student.name} is missing enrollment in one or more trimester groups")
            failures_count += 1
            continue
        
        students_processed += 1
        
        # Remove existing trimester course assignments for this student
        Enrollment.objects.filter(
            student=student,
            section__course__in=all_trimester_courses
        ).delete()
        
        # Try to assign trimester courses
        success, message, assignments = assign_trimester_courses(student, group_ids)
        
        if success:
            assignments_count += len(assignments)
        else:
            print(f"Failed to assign trimester courses for {student.name}: {message}")
            failures_count += 1
    
    print(f"Processed trimester courses for {students_processed} students")
    print(f"Created {assignments_count} trimester course assignments")
    print(f"Failed to assign trimester courses for {failures_count} students")
    
    return {
        'assignments': assignments_count,
        'failures': failures_count
    }

def handle_language_course_assignment(course):
    """Handle assignments for a single language course."""
    from schedule.utils.language_course_utils import assign_language_courses
    
    assignments_count = 0
    failures_count = 0
    
    # Get language courses for this grade level
    language_courses = Course.objects.filter(
        type='language', 
        grade_level=course.grade_level
    )
    
    # Get students enrolled in this course
    students = Student.objects.filter(
        course_enrollments__course=course
    ).distinct()
    
    for student in students:
        # Get student's language course enrollments
        enrolled_courses = Course.objects.filter(
            student_enrollments__student=student,
            type='language'
        )
        
        # Skip if no language course enrollments
        if enrolled_courses.count() <= 1:
            continue
        
        # Remove existing language course assignments
        Enrollment.objects.filter(
            student=student,
            section__course__in=language_courses
        ).delete()
        
        # Try to assign language courses
        success, message, assignments = assign_language_courses(student, enrolled_courses.all())
        
        if success:
            assignments_count += len(assignments)
        else:
            failures_count += 1
    
    return {
        'status': 'success',
        'message': f'Processed language course {course.id}',
        'initial_assignments': assignments_count,
        'initial_failures': failures_count,
        'conflicts_resolved': 0,
        'unresolvable_conflicts': 0,
        'errors': []
    }

def handle_trimester_course_assignment(course):
    """Handle assignments for a single trimester course."""
    from schedule.utils.trimester_course_utils import assign_trimester_courses
    from schedule.models import TrimesterCourseGroup
    
    assignments_count = 0
    failures_count = 0
    
    # Find which trimester group this course belongs to
    group = TrimesterCourseGroup.objects.filter(courses=course).first()
    if not group:
        return {
            'status': 'error',
            'message': f'Course {course.id} is not part of any trimester group',
            'initial_assignments': 0,
            'initial_failures': 0,
            'conflicts_resolved': 0,
            'unresolvable_conflicts': 0,
            'errors': [f'Course {course.id} is not part of any trimester group']
        }
    
    # Get all trimester groups
    all_groups = TrimesterCourseGroup.objects.all()
    group_ids = list(all_groups.values_list('id', flat=True))
    
    # Get all courses in these groups
    all_trimester_courses = []
    for g in all_groups:
        all_trimester_courses.extend(list(g.courses.all()))
    
    # Get students enrolled in this course
    students = Student.objects.filter(
        course_enrollments__course=course
    ).distinct()
    
    for student in students:
        # Remove existing trimester course assignments
        Enrollment.objects.filter(
            student=student,
            section__course__in=all_trimester_courses
        ).delete()
        
        # Try to assign trimester courses
        success, message, assignments = assign_trimester_courses(student, group_ids)
        
        if success:
            assignments_count += len(assignments)
        else:
            failures_count += 1
    
    return {
        'status': 'success',
        'message': f'Processed trimester course {course.id}',
        'initial_assignments': assignments_count,
        'initial_failures': failures_count,
        'conflicts_resolved': 0,
        'unresolvable_conflicts': 0,
        'errors': []
    } 