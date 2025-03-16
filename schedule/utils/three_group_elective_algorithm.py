"""
Advanced algorithm for registering students to three elective course groups.
This module implements an algorithm that ensures all selected courses are in the same period.
"""
from django.db import transaction
from schedule.models import Student, Course, Section, Enrollment, CourseEnrollment, Period
import logging
from collections import defaultdict

# Set up logging
logger = logging.getLogger(__name__)

def register_students_to_three_groups(students, first_group_sections, second_group_sections, third_group_sections, undo_depth=3, max_iterations=None):
    """
    Register students to three course groups ensuring all selected courses are in the same period.
    
    The algorithm works as follows:
    1. For each student, find periods that have sections from all three course groups
    2. For each compatible period, assign the student to one section from each group
    3. Prioritize even distribution across sections
    4. Use backtracking when a student can't be placed
    
    Args:
        students: List of Student objects to register
        first_group_sections: Dictionary mapping course IDs to lists of Section objects (first group - Art/Music/WW)
        second_group_sections: Dictionary mapping course IDs to lists of Section objects (second group - Health & Wellness)
        third_group_sections: Dictionary mapping course IDs to lists of Section objects (third group - Coding & Theatre Arts)
        undo_depth: Number of registrations to undo when backtracking (default: 3)
        max_iterations: Maximum number of iterations before giving up (defaults to number of students)
        
    Returns:
        tuple: (success, message, assignments)
            - success: Boolean indicating if all assignments were successful
            - message: Status message
            - assignments: List of created Enrollment objects
    """
    print(f"DEBUG: Starting registration for {len(students)} students to three course groups")
    print(f"DEBUG: First group sections: {', '.join([f'{c_id}({len(secs)})' for c_id, secs in first_group_sections.items()])}")
    print(f"DEBUG: Second group sections: {', '.join([f'{c_id}({len(secs)})' for c_id, secs in second_group_sections.items()])}")
    print(f"DEBUG: Third group sections: {', '.join([f'{c_id}({len(secs)})' for c_id, secs in third_group_sections.items()])}")
    
    if max_iterations is None:
        max_iterations = len(students) * 4  # More iterations since this is more complex
    
    # Organize sections by period for easy access
    first_group_by_period = defaultdict(list)
    second_group_by_period = defaultdict(list)
    third_group_by_period = defaultdict(list)
    
    # First group sections by period (Art/Music/WW)
    for course_id, sections in first_group_sections.items():
        for section in sections:
            if section.period:
                first_group_by_period[section.period.id].append({
                    'section': section,
                    'course_id': course_id,
                    'current_enrollment': Enrollment.objects.filter(section=section).count(),
                    'max_size': section.max_size if section.max_size is not None else 25,
                    'exact_size': section.exact_size
                })
    
    # Second group sections by period (Health & Wellness)
    for course_id, sections in second_group_sections.items():
        for section in sections:
            if section.period:
                second_group_by_period[section.period.id].append({
                    'section': section,
                    'course_id': course_id,
                    'current_enrollment': Enrollment.objects.filter(section=section).count(),
                    'max_size': section.max_size if section.max_size is not None else 25,
                    'exact_size': section.exact_size
                })
    
    # Third group sections by period (Coding & Theatre Arts)
    for course_id, sections in third_group_sections.items():
        for section in sections:
            if section.period:
                third_group_by_period[section.period.id].append({
                    'section': section,
                    'course_id': course_id,
                    'current_enrollment': Enrollment.objects.filter(section=section).count(),
                    'max_size': section.max_size if section.max_size is not None else 25,
                    'exact_size': section.exact_size
                })
    
    # Find periods that have all three group sections
    common_periods = set(first_group_by_period.keys()) & set(second_group_by_period.keys()) & set(third_group_by_period.keys())
    print(f"DEBUG: Found {len(common_periods)} periods with sections from all three groups")
    
    if not common_periods:
        return False, "No common periods found with sections from all three groups", []
    
    # Track assignments for potential backtracking
    assignments = []
    assignment_history = []
    
    def get_best_section(period_id, group_sections, existing_assignments=None):
        """Get the best section from the given period, considering enrollment balance."""
        available_sections = []
        
        for section_data in group_sections[period_id]:
            # Check if the section has space
            current_enrollment = section_data['current_enrollment']
            max_size = section_data['max_size']
            
            # Consider exact_size if set
            exact_size = section_data['exact_size']
            has_exact_size = exact_size is not None
            
            # Skip if section is full
            if current_enrollment >= max_size:
                continue
                
            # Skip if student is already enrolled in this course
            if existing_assignments and section_data['course_id'] in [a[1] for a in existing_assignments]:
                continue
                
            # Check if section has met exact_size target
            if has_exact_size and current_enrollment >= exact_size:
                # Only add if we absolutely have to (no other options)
                if not available_sections:
                    available_sections.append({
                        'section': section_data['section'],
                        'course_id': section_data['course_id'],
                        'open_seats': max_size - current_enrollment,
                        'remaining_to_target': 0,
                        'has_exact_size': has_exact_size
                    })
            else:
                # Calculate target - if exact_size is set, use it, otherwise use max_size
                target = exact_size if has_exact_size else max_size
                remaining_to_target = target - current_enrollment
                
                available_sections.append({
                    'section': section_data['section'],
                    'course_id': section_data['course_id'],
                    'open_seats': max_size - current_enrollment,
                    'remaining_to_target': remaining_to_target,
                    'has_exact_size': has_exact_size
                })
        
        if not available_sections:
            return None
            
        # Prioritize sections with exact_size that haven't reached their target
        exact_size_sections = [s for s in available_sections if s['has_exact_size'] and s['remaining_to_target'] > 0]
        if exact_size_sections:
            # Sort by how far they are from their target (descending)
            return sorted(exact_size_sections, key=lambda s: -s['remaining_to_target'])[0]
            
        # Otherwise, sort by open seats (descending) to balance enrollment
        return sorted(available_sections, key=lambda s: -s['open_seats'])[0]
    
    def register_student_to_period(student, period_id):
        """Register a student to sections from all three groups in the given period."""
        # Get best section from first group
        first_section = get_best_section(period_id, first_group_by_period)
        if not first_section:
            print(f"DEBUG: Failed to find section in first group for period {period_id}")
            return False, []
            
        # Get best section from second group
        second_section = get_best_section(period_id, second_group_by_period, [(first_section['section'], first_section['course_id'])])
        if not second_section:
            print(f"DEBUG: Failed to find section in second group for period {period_id}")
            return False, []
            
        # Get best section from third group
        third_section = get_best_section(period_id, third_group_by_period, [
            (first_section['section'], first_section['course_id']),
            (second_section['section'], second_section['course_id'])
        ])
        if not third_section:
            print(f"DEBUG: Failed to find section in third group for period {period_id}")
            return False, []
        
        # Create enrollments
        new_assignments = []
        
        # Check if student is already enrolled in first section
        if not Enrollment.objects.filter(student=student, section=first_section['section']).exists():
            # Enroll in first section
            enrollment1 = Enrollment.objects.create(student=student, section=first_section['section'])
            new_assignments.append(enrollment1)
            
            # Update course enrollment stats
            for section_data in first_group_by_period[period_id]:
                if section_data['section'] == first_section['section']:
                    section_data['current_enrollment'] += 1
        else:
            print(f"DEBUG: Student {student.id} already enrolled in section {first_section['section'].id}")
            
        # Check if student is already enrolled in second section
        if not Enrollment.objects.filter(student=student, section=second_section['section']).exists():
            # Enroll in second section
            enrollment2 = Enrollment.objects.create(student=student, section=second_section['section'])
            new_assignments.append(enrollment2)
            
            # Update course enrollment stats
            for section_data in second_group_by_period[period_id]:
                if section_data['section'] == second_section['section']:
                    section_data['current_enrollment'] += 1
        else:
            print(f"DEBUG: Student {student.id} already enrolled in section {second_section['section'].id}")
            
        # Check if student is already enrolled in third section
        if not Enrollment.objects.filter(student=student, section=third_section['section']).exists():
            # Enroll in third section
            enrollment3 = Enrollment.objects.create(student=student, section=third_section['section'])
            new_assignments.append(enrollment3)
            
            # Update course enrollment stats
            for section_data in third_group_by_period[period_id]:
                if section_data['section'] == third_section['section']:
                    section_data['current_enrollment'] += 1
        else:
            print(f"DEBUG: Student {student.id} already enrolled in section {third_section['section'].id}")
        
        # Only add to assignments history if we actually created new enrollments
        if new_assignments:
            assignments.extend(new_assignments)
            assignment_history.append((student, period_id, [
                (first_section['section'], first_section['course_id']),
                (second_section['section'], second_section['course_id']),
                (third_section['section'], third_section['course_id'])
            ]))
            
            print(f"DEBUG: Registered student {student.id} to period {period_id}: {first_section['section'].id}, {second_section['section'].id}, and {third_section['section'].id}")
            return True, new_assignments
        else:
            # If student was already enrolled in all sections, consider this a success
            print(f"DEBUG: Student {student.id} was already enrolled in all three sections")
            return True, []
    
    def undo_registrations(count):
        """Undo the last 'count' students' registrations."""
        if not assignments:
            print("DEBUG: No assignments to undo")
            return
            
        students_to_undo = min(count, len(assignment_history))
        print(f"DEBUG: Undoing registrations for {students_to_undo} students")
        
        for _ in range(students_to_undo):
            if not assignment_history:
                break
                
            last_record = assignment_history.pop()
            student, period_id, sections_info = last_record
            
            print(f"DEBUG: Undoing registration of student {student.id} in period {period_id}")
            
            # Remove three enrollments per student (one from each group)
            for _ in range(3):
                if not assignments:
                    break
                    
                last_enrollment = assignments.pop()
                
                # Update enrollment counts
                section = last_enrollment.section
                
                if period_id in first_group_by_period:
                    for section_data in first_group_by_period[period_id]:
                        if section_data['section'] == section:
                            section_data['current_enrollment'] -= 1
                            
                if period_id in second_group_by_period:
                    for section_data in second_group_by_period[period_id]:
                        if section_data['section'] == section:
                            section_data['current_enrollment'] -= 1
                            
                if period_id in third_group_by_period:
                    for section_data in third_group_by_period[period_id]:
                        if section_data['section'] == section:
                            section_data['current_enrollment'] -= 1
                
                # Delete enrollment
                last_enrollment.delete()
    
    with transaction.atomic():
        iteration_count = 0
        student_index = 0
        
        # Process each student
        while student_index < len(students) and iteration_count < max_iterations:
            student = students[student_index]
            
            print(f"DEBUG: Processing student {student.id} ({student_index + 1}/{len(students)})")
            
            # Try each period that has sections from all three groups
            success = False
            for period_id in common_periods:
                registration_success, _ = register_student_to_period(student, period_id)
                if registration_success:
                    success = True
                    break
            
            if success:
                # Successfully registered student to all three groups, move to next student
                print(f"DEBUG: Successfully registered student {student.id} to all three course groups")
                student_index += 1
            else:
                # Failed to register this student in any period
                print(f"DEBUG: Failed to register student {student.id}, backtracking...")
                undo_registrations(undo_depth)
            
            iteration_count += 1
            if iteration_count % 10 == 0:
                print(f"DEBUG: Iteration {iteration_count}, processed {student_index}/{len(students)} students")
    
    print(f"DEBUG: Completed with {student_index}/{len(students)} students successfully registered")
    if student_index == len(students):
        return True, f"Successfully registered all {len(students)} students to all three course groups", assignments
    else:
        return False, f"Failed to register all students. Completed {student_index}/{len(students)}", assignments

def register_three_elective_groups(grade_level, undo_depth=3):
    """
    Register students to Art/Music/WW, Health/Wellness, and Coding/Theatre courses ensuring all are in the same period.
    
    Args:
        grade_level: The grade level to register (e.g., 6 for 6th grade)
        undo_depth: Number of registrations to undo when backtracking
        
    Returns:
        dict: Registration results with success and failure counts
    """
    print(f"DEBUG: Starting three-group elective registration for grade {grade_level}")
    
    # Get students for this grade level
    students = Student.objects.filter(grade_level=grade_level)
    print(f"DEBUG: Found {students.count()} students in grade {grade_level}")
    
    if students.count() == 0:
        return {
            'status': 'error',
            'message': f'No students found for grade {grade_level}',
            'amw_success': 0,
            'amw_failure': 0,
            'hw_success': 0,
            'hw_failure': 0,
            'coding_theatre_success': 0,
            'coding_theatre_failure': 0
        }
    
    # Get Art/Music/WW courses
    amw_courses = Course.objects.filter(
        id__in=['ART6', 'MUS6', 'WW6'],
        grade_level=grade_level
    )
    print(f"DEBUG: Found {amw_courses.count()} Art/Music/WW courses")
    
    # Get Health & Wellness courses
    hw_courses = Course.objects.filter(
        id__in=['HW6', 'WH6'],
        grade_level=grade_level
    )
    print(f"DEBUG: Found {hw_courses.count()} Health & Wellness courses")
    
    # Get Coding & Theatre Arts courses
    coding_theatre_courses = Course.objects.filter(
        id__in=['CODE6', 'THEA6'],
        grade_level=grade_level
    )
    print(f"DEBUG: Found {coding_theatre_courses.count()} Coding & Theatre Arts courses")
    
    # Combine all course lists
    amw_course_list = list(amw_courses)
    hw_course_list = list(hw_courses)
    coding_theatre_course_list = list(coding_theatre_courses)
    all_courses = amw_course_list + hw_course_list + coding_theatre_course_list
    
    # Check if we have courses from each group
    error_message = None
    if not amw_course_list:
        error_message = 'No Art/Music/WW courses found'
    elif not hw_course_list:
        error_message = 'No Health & Wellness courses found'
    elif not coding_theatre_course_list:
        error_message = 'No Coding & Theatre Arts courses found'
        
    if error_message:
        return {
            'status': 'error',
            'message': error_message,
            'amw_success': 0,
            'amw_failure': len(students),
            'hw_success': 0,
            'hw_failure': len(students),
            'coding_theatre_success': 0,
            'coding_theatre_failure': len(students)
        }
    
    # Get sections for each course group
    amw_sections = {}
    hw_sections = {}
    coding_theatre_sections = {}
    
    # Get Art/Music/WW sections
    for course in amw_course_list:
        sections = Section.objects.filter(course=course)
        if sections.exists():
            amw_sections[course.id] = list(sections)
            print(f"DEBUG: Found {sections.count()} sections for {course.id}")
        else:
            print(f"DEBUG: No sections found for {course.id}")
    
    # Get Health & Wellness sections
    for course in hw_course_list:
        sections = Section.objects.filter(course=course)
        if sections.exists():
            hw_sections[course.id] = list(sections)
            print(f"DEBUG: Found {sections.count()} sections for {course.id}")
        else:
            print(f"DEBUG: No sections found for {course.id}")
    
    # Get Coding & Theatre Arts sections
    for course in coding_theatre_course_list:
        sections = Section.objects.filter(course=course)
        if sections.exists():
            coding_theatre_sections[course.id] = list(sections)
            print(f"DEBUG: Found {sections.count()} sections for {course.id}")
        else:
            print(f"DEBUG: No sections found for {course.id}")
    
    # Ensure we have sections for at least one course in each group
    if not amw_sections:
        return {
            'status': 'error',
            'message': 'No sections found for Art/Music/WW courses',
            'amw_success': 0,
            'amw_failure': len(students),
            'hw_success': 0,
            'hw_failure': len(students),
            'coding_theatre_success': 0,
            'coding_theatre_failure': len(students)
        }
    
    if not hw_sections:
        return {
            'status': 'error',
            'message': 'No sections found for Health & Wellness courses',
            'amw_success': 0,
            'amw_failure': len(students),
            'hw_success': 0,
            'hw_failure': len(students),
            'coding_theatre_success': 0,
            'coding_theatre_failure': len(students)
        }
    
    if not coding_theatre_sections:
        return {
            'status': 'error',
            'message': 'No sections found for Coding & Theatre Arts courses',
            'amw_success': 0,
            'amw_failure': len(students),
            'hw_success': 0,
            'hw_failure': len(students),
            'coding_theatre_success': 0,
            'coding_theatre_failure': len(students)
        }
    
    # Check if students are already enrolled in these courses
    all_course_ids = [course.id for course in all_courses]
    student_course_enrollments = {}
    
    for student in students:
        student_course_enrollments[student.id] = set()
    
    # Get existing course enrollments
    existing_enrollments = CourseEnrollment.objects.filter(
        student__in=students,
        course__id__in=all_course_ids
    )
    
    # Count existing enrollments
    for enrollment in existing_enrollments:
        student_course_enrollments[enrollment.student_id].add(enrollment.course_id)
    
    # Check existing section enrollments to avoid duplicates
    existing_section_enrollments = Enrollment.objects.filter(
        student__in=students,
        section__course__id__in=all_course_ids
    ).select_related('student', 'section__course')
    
    # Track students who already have section enrollments by course group
    students_with_amw_sections = set()
    students_with_hw_sections = set()
    students_with_coding_theatre_sections = set()
    
    for enrollment in existing_section_enrollments:
        course_id = enrollment.section.course.id
        student_id = enrollment.student.id
        
        if course_id in [c.id for c in amw_course_list]:
            students_with_amw_sections.add(student_id)
        elif course_id in [c.id for c in hw_course_list]:
            students_with_hw_sections.add(student_id)
        elif course_id in [c.id for c in coding_theatre_course_list]:
            students_with_coding_theatre_sections.add(student_id)
    
    # Filter out students who already have enrollments in all course groups
    students_to_process = [s for s in students if not (
        s.id in students_with_amw_sections and 
        s.id in students_with_hw_sections and 
        s.id in students_with_coding_theatre_sections
    )]
    
    if len(students_to_process) < len(students):
        print(f"DEBUG: Skipping {len(students) - len(students_to_process)} students who already have enrollments in all course groups")
    
    # Create missing course enrollments
    for student in students_to_process:
        # Ensure each student is enrolled in at least one Art/Music/WW course
        amw_enrolled = any(course_id in student_course_enrollments[student.id] for course_id in [c.id for c in amw_course_list])
        if not amw_enrolled and amw_course_list:
            # Enroll in the first available Art/Music/WW course
            course = amw_course_list[0]
            print(f"DEBUG: Creating course enrollment for student {student.id} in AMW course {course.id}")
            CourseEnrollment.objects.create(student=student, course=course)
            student_course_enrollments[student.id].add(course.id)
        
        # Ensure each student is enrolled in at least one Health & Wellness course
        hw_enrolled = any(course_id in student_course_enrollments[student.id] for course_id in [c.id for c in hw_course_list])
        if not hw_enrolled and hw_course_list:
            # Enroll in the first available Health & Wellness course
            course = hw_course_list[0]
            print(f"DEBUG: Creating course enrollment for student {student.id} in HW course {course.id}")
            CourseEnrollment.objects.create(student=student, course=course)
            student_course_enrollments[student.id].add(course.id)
            
        # Ensure each student is enrolled in at least one Coding & Theatre Arts course
        coding_theatre_enrolled = any(course_id in student_course_enrollments[student.id] for course_id in [c.id for c in coding_theatre_course_list])
        if not coding_theatre_enrolled and coding_theatre_course_list:
            # Enroll in the first available Coding & Theatre Arts course
            course = coding_theatre_course_list[0]
            print(f"DEBUG: Creating course enrollment for student {student.id} in Coding/Theatre course {course.id}")
            CourseEnrollment.objects.create(student=student, course=course)
            student_course_enrollments[student.id].add(course.id)
    
    # Run the three-group registration algorithm
    print(f"DEBUG: Starting registration algorithm for {len(students_to_process)} students")
    success, message, assignments = register_students_to_three_groups(
        students_to_process,
        amw_sections,
        hw_sections,
        coding_theatre_sections,
        undo_depth=undo_depth,
        max_iterations=len(students_to_process) * 5  # Allow more iterations for complex schedules
    )
    
    if success:
        print(f"DEBUG: Registration successful for all {len(students_to_process)} students")
        return {
            'status': 'success',
            'message': 'Successfully registered all students to all three course groups',
            'amw_success': len(students_to_process),
            'amw_failure': 0,
            'hw_success': len(students_to_process),
            'hw_failure': 0,
            'coding_theatre_success': len(students_to_process),
            'coding_theatre_failure': 0
        }
    else:
        # Count successful registrations by course group
        print(f"DEBUG: Partial success, counting successful registrations")
        
        # Get unique students with Art/Music/WW course assignments
        amw_enrolled_students = set()
        for course in amw_course_list:
            enrolled = set(Enrollment.objects.filter(
                section__course=course,
                student__in=students_to_process
            ).values_list('student_id', flat=True))
            amw_enrolled_students.update(enrolled)
        
        # Get unique students with Health & Wellness course assignments
        hw_enrolled_students = set()
        for course in hw_course_list:
            enrolled = set(Enrollment.objects.filter(
                section__course=course,
                student__in=students_to_process
            ).values_list('student_id', flat=True))
            hw_enrolled_students.update(enrolled)
            
        # Get unique students with Coding & Theatre Arts course assignments
        coding_theatre_enrolled_students = set()
        for course in coding_theatre_course_list:
            enrolled = set(Enrollment.objects.filter(
                section__course=course,
                student__in=students_to_process
            ).values_list('student_id', flat=True))
            coding_theatre_enrolled_students.update(enrolled)
            
        amw_success = len(amw_enrolled_students)
        hw_success = len(hw_enrolled_students)
        coding_theatre_success = len(coding_theatre_enrolled_students)
        
        print(f"DEBUG: Art/Music/WW success: {amw_success}/{len(students_to_process)}")
        print(f"DEBUG: Health & Wellness success: {hw_success}/{len(students_to_process)}")
        print(f"DEBUG: Coding & Theatre Arts success: {coding_theatre_success}/{len(students_to_process)}")
        
        return {
            'status': 'partial',
            'message': message,
            'amw_success': amw_success,
            'amw_failure': len(students_to_process) - amw_success,
            'hw_success': hw_success,
            'hw_failure': len(students_to_process) - hw_success,
            'coding_theatre_success': coding_theatre_success,
            'coding_theatre_failure': len(students_to_process) - coding_theatre_success
        } 