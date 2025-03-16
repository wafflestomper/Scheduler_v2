from django.db.models import Count
from schedule.models import Student, Course, TrimesterCourseGroup, Period, Section, Enrollment, CourseEnrollment
import random

def assign_trimester_courses(student, group_ids=None, preferred_period=None):
    """
    Assigns a student to trimester course sections using backtracking algorithm:
    - One course from each group (WH6/HW6, CTA6/TAC6, WW6/Art6/Mus6)
    - Each course in a different trimester
    - All courses in the same period
    
    Args:
        student: The Student object to assign
        group_ids: Optional list of TrimesterCourseGroup IDs to include
        preferred_period: Optional preferred Period object
        
    Returns:
        tuple: (success, message, assignments)
            - success: Boolean indicating if assignment was successful
            - message: Status message
            - assignments: List of created Enrollment objects
    """
    # Get the trimester course groups if none provided
    if group_ids:
        trimester_groups = TrimesterCourseGroup.objects.filter(id__in=group_ids)
    else:
        # Default to all groups for 6th grade
        trimester_groups = TrimesterCourseGroup.objects.all()
    
    # Get all courses in these groups
    all_courses = []
    for group in trimester_groups:
        courses = list(group.courses.all())
        all_courses.extend(courses)
    
    # Ensure student is enrolled in at least one course from each group
    for group in trimester_groups:
        # Check if student is enrolled in any course from this group
        enrolled_in_group = CourseEnrollment.objects.filter(
            student=student,
            course__in=group.courses.all()
        ).exists()
        
        if not enrolled_in_group:
            return (False, f"Student not enrolled in any course from group: {group.name}", [])
    
    # Check if student already has any trimester course section assignments
    existing_assignments = Enrollment.objects.filter(
        student=student,
        section__course__in=all_courses
    ).select_related('section', 'section__course', 'section__period')
    
    # If student already has assignments, handle them
    if existing_assignments.exists():
        return handle_existing_assignments(student, existing_assignments, trimester_groups)
    
    # Get all available sections for these courses
    course_sections = Section.objects.filter(
        course__in=all_courses
    ).select_related('course', 'period')
    
    # Get the student's enrolled courses for each group
    student_courses = []
    for group in trimester_groups:
        enrolled_course = CourseEnrollment.objects.filter(
            student=student,
            course__in=group.courses.all()
        ).first()
        
        if enrolled_course:
            student_courses.append(enrolled_course.course)
    
    # Organize sections by period, trimester, and course
    # This will be our constraint model for backtracking
    sections_by_period = {}
    
    # First, gather all sections and organize them
    for section in course_sections:
        if section.period_id not in sections_by_period:
            sections_by_period[section.period_id] = {
                'period': section.period,
                'trimesters': {'t1': {}, 't2': {}, 't3': {}}
            }
        
        period_data = sections_by_period[section.period_id]
        trimester = section.when
        
        # Skip if this course isn't one of the student's enrolled courses
        student_course_ids = [c.id for c in student_courses]
        if section.course_id not in student_course_ids:
            continue
            
        # Add section to this period/trimester
        if section.course_id not in period_data['trimesters'][trimester]:
            period_data['trimesters'][trimester][section.course_id] = {
                'section': section,
                'enrollment': section.students.count(),
                'max_size': section.max_size
            }
    
    # Prioritize the preferred period if specified
    period_ids = list(sections_by_period.keys())
    if preferred_period and preferred_period.id in period_ids:
        # Move preferred period to front of list
        period_ids.remove(preferred_period.id)
        period_ids.insert(0, preferred_period.id)
    
    # Sort student courses by restrictiveness (sections with fewer spots first)
    restrictiveness = {}
    for course in student_courses:
        course_sections = Section.objects.filter(course=course)
        total_capacity = sum(s.max_size or 100 for s in course_sections)
        restrictiveness[course.id] = total_capacity
    
    sorted_student_courses = sorted(student_courses, key=lambda c: restrictiveness.get(c.id, float('inf')))
    
    # Now try to find a valid assignment using backtracking
    assignments = []
    solution = backtrack_assign_courses(student, sorted_student_courses, sections_by_period, period_ids)
    
    if solution:
        # Create the enrollments
        for trimester, section in solution.items():
            enrollment = Enrollment.objects.create(
                student=student,
                section=section
            )
            assignments.append(enrollment)
        
        return (True, "Successfully assigned all courses", assignments)
    else:
        # Try a different approach: find sections with available space one by one
        success, assignments = assign_courses_greedily(student, student_courses, sections_by_period, period_ids)
        if success:
            return (True, "Successfully assigned courses using greedy approach", assignments)
        else:
            return (False, "Failed to find valid assignment after trying all approaches", [])


def backtrack_assign_courses(student, courses, sections_by_period, period_ids):
    """
    Uses backtracking to find a valid assignment of courses to trimesters within a period.
    
    Args:
        student: The Student object to assign
        courses: List of Course objects to assign, sorted by restrictiveness
        sections_by_period: Dict of period data with available sections
        period_ids: List of period IDs to try, in priority order
    
    Returns:
        dict: Map of trimester -> section if successful, None otherwise
    """
    # Try each period in order
    for period_id in period_ids:
        # Check if this period has sections for all required courses
        period_data = sections_by_period[period_id]
        
        # Attempt to assign courses within this period
        assignment = backtrack_helper(student, courses, period_data, {})
        if assignment:
            return assignment
    
    return None


def backtrack_helper(student, remaining_courses, period_data, current_assignment):
    """
    Recursive helper for backtracking algorithm.
    
    Args:
        student: The Student object to assign
        remaining_courses: List of remaining Course objects to assign
        period_data: Dict with period and trimester section data
        current_assignment: Dict mapping trimester -> section for courses already assigned
    
    Returns:
        dict: Updated assignment if successful, None otherwise
    """
    # Base case: all courses assigned
    if not remaining_courses:
        return current_assignment
    
    # Get the next course to assign (most restrictive first)
    current_course = remaining_courses[0]
    next_courses = remaining_courses[1:]
    
    # Get available trimesters (those not already assigned)
    assigned_trimesters = set(current_assignment.keys())
    available_trimesters = [t for t in ['t1', 't2', 't3'] if t not in assigned_trimesters]
    
    # Try each available trimester for this course
    for trimester in available_trimesters:
        # Check if this course has a section in this trimester for this period
        if current_course.id in period_data['trimesters'][trimester]:
            section_data = period_data['trimesters'][trimester][current_course.id]
            section = section_data['section']
            
            # Check if section has space
            if section_data['max_size'] is None or section_data['enrollment'] < section_data['max_size']:
                # Try this assignment
                new_assignment = current_assignment.copy()
                new_assignment[trimester] = section
                
                # Recursively assign remaining courses
                result = backtrack_helper(student, next_courses, period_data, new_assignment)
                if result:
                    return result
    
    # If we get here, no valid assignment was found
    return None


def assign_courses_greedily(student, courses, sections_by_period, period_ids):
    """
    Fallback greedy algorithm that tries to find any working assignment,
    even if it means assigning to different periods.
    
    Returns:
        tuple: (success, assignments)
    """
    # Try to find any sections with space for each course
    assignments = []
    assigned_trimesters = set()
    
    # Randomize course order for multiple attempts
    for attempt in range(3):  # Try 3 times with different orderings
        assignments = []
        assigned_trimesters = set()
        shuffled_courses = list(courses)
        random.shuffle(shuffled_courses)
        
        for course in shuffled_courses:
            # Find any section for this course that doesn't conflict
            section_found = False
            
            # Try all periods (in priority order)
            for period_id in period_ids:
                if section_found:
                    break
                    
                period_data = sections_by_period[period_id]
                
                # Try each trimester not already assigned
                for trimester in ['t1', 't2', 't3']:
                    if trimester in assigned_trimesters:
                        continue
                        
                    if course.id in period_data['trimesters'][trimester]:
                        section_data = period_data['trimesters'][trimester][course.id]
                        
                        # Check if section has space
                        if section_data['max_size'] is None or section_data['enrollment'] < section_data['max_size']:
                            # Create enrollment
                            enrollment = Enrollment.objects.create(
                                student=student,
                                section=section_data['section']
                            )
                            assignments.append(enrollment)
                            assigned_trimesters.add(trimester)
                            section_found = True
                            break
            
            if not section_found:
                # If we failed to assign this course, undo enrollments and try again
                for enrollment in assignments:
                    enrollment.delete()
                assignments = []
                assigned_trimesters = set()
                break
        
        # If we successfully assigned all courses, return success
        if len(assignments) == len(courses):
            return True, assignments
    
    # If we get here, we couldn't assign all courses
    return False, []


def handle_existing_assignments(student, existing_assignments, trimester_groups):
    """
    Handle case where student already has some trimester course assignments.
    Try to complete the assignments if possible.
    """
    existing_period = None
    assigned_trimesters = {}
    assigned_courses = {}
    assigned_groups = {}
    new_assignments = []
    
    for enrollment in existing_assignments:
        section = enrollment.section
        course_id = section.course_id
        trimester = section.when
        period_id = section.period_id
        
        # Find which group this course belongs to
        for group in trimester_groups:
            if group.courses.filter(id=course_id).exists():
                assigned_groups[group.id] = course_id
                break
        
        assigned_courses[course_id] = {
            'section': section,
            'trimester': trimester,
            'period': period_id
        }
        
        if existing_period is None:
            existing_period = period_id
        elif existing_period != period_id:
            return (False, f"Student has trimester courses in different periods", new_assignments)
        
        assigned_trimesters[trimester] = course_id
    
    # Identify missing group assignments
    missing_groups = []
    for group in trimester_groups:
        if group.id not in assigned_groups:
            missing_groups.append(group)
    
    available_trimesters = set(['t1', 't2', 't3']) - set(assigned_trimesters.keys())
    
    if len(missing_groups) != len(available_trimesters):
        return (False, "Mismatched missing groups and trimesters", new_assignments)
    
    # Get all sections for the missing groups in the existing period
    course_sections = Section.objects.filter(
        course__course_groups__in=missing_groups,
        period_id=existing_period
    ).select_related('course')
    
    # Organize by trimester and course
    sections_by_trimester_course = {}
    for section in course_sections:
        trimester = section.when
        if trimester not in sections_by_trimester_course:
            sections_by_trimester_course[trimester] = {}
        
        sections_by_trimester_course[trimester][section.course_id] = {
            'section': section,
            'enrollment': section.students.count(),
            'max_size': section.max_size
        }
    
    # Get student's enrolled courses for each missing group
    student_courses = []
    for group in missing_groups:
        enrolled_course = CourseEnrollment.objects.filter(
            student=student,
            course__in=group.courses.all()
        ).first()
        
        if enrolled_course:
            student_courses.append(enrolled_course.course)
    
    # Try to assign each missing course to an available trimester
    successful = True
    
    for course in student_courses:
        course_assigned = False
        for trimester in available_trimesters:
            if trimester in sections_by_trimester_course and course.id in sections_by_trimester_course[trimester]:
                section_data = sections_by_trimester_course[trimester][course.id]
                
                # Check if section has space
                if section_data['max_size'] is None or section_data['enrollment'] < section_data['max_size']:
                    # Create enrollment
                    enrollment = Enrollment.objects.create(
                        student=student,
                        section=section_data['section']
                    )
                    new_assignments.append(enrollment)
                    available_trimesters.remove(trimester)
                    course_assigned = True
                    break
        
        if not course_assigned:
            successful = False
            break
    
    if successful:
        return (True, "Completed partial assignments", new_assignments)
    else:
        # Clean up any partial assignments we created
        for enrollment in new_assignments:
            enrollment.delete()
        
        return (False, "Could not complete all assignments", [])


def get_trimester_course_conflicts(student, group_ids=None):
    """
    Check for conflicts in a student's trimester course assignments
    
    Args:
        student: The Student object to check
        group_ids: Optional list of TrimesterCourseGroup IDs to check
        
    Returns:
        list: List of conflict messages
    """
    conflicts = []
    
    # Get the trimester course groups
    if group_ids:
        trimester_groups = TrimesterCourseGroup.objects.filter(id__in=group_ids)
    else:
        # Default to all groups
        trimester_groups = TrimesterCourseGroup.objects.all()
    
    # Get all courses in these groups
    all_courses = []
    for group in trimester_groups:
        courses = list(group.courses.all())
        all_courses.extend(courses)
    
    # Get student's enrollments for these courses
    enrollments = Enrollment.objects.filter(
        student=student,
        section__course__in=all_courses
    ).select_related('section', 'section__course', 'section__period')
    
    if not enrollments.exists():
        return conflicts
    
    # Check for period consistency
    periods = set()
    for enrollment in enrollments:
        periods.add(enrollment.section.period_id)
    
    if len(periods) > 1:
        conflicts.append(f"Student has trimester courses in {len(periods)} different periods")
    
    # Check for trimester conflicts
    trimester_courses = {}
    for enrollment in enrollments:
        trimester = enrollment.section.when
        if trimester not in trimester_courses:
            trimester_courses[trimester] = []
        trimester_courses[trimester].append(enrollment.section.course.id)
    
    for trimester, courses in trimester_courses.items():
        if len(courses) > 1:
            conflicts.append(f"Student has multiple trimester courses in {trimester}: {', '.join(courses)}")
    
    # Check for missing group assignments
    assigned_groups = set()
    for enrollment in enrollments:
        course_id = enrollment.section.course_id
        for group in trimester_groups:
            if group.courses.filter(id=course_id).exists():
                assigned_groups.add(group.id)
    
    missing_groups = []
    for group in trimester_groups:
        if group.id not in assigned_groups:
            missing_groups.append(group.name)
    
    if missing_groups:
        conflicts.append(f"Student missing assignments for groups: {', '.join(missing_groups)}")
    
    return conflicts


def balance_trimester_course_sections():
    """
    Balance student distribution across trimester course sections.
    Attempts to keep section sizes as even as possible while maintaining constraints.
    
    Returns:
        dict: Statistics on the balancing operation
    """
    stats = {
        'moved_students': 0,
        'total_students': 0,
        'conflicts_resolved': 0,
    }
    
    # Get all trimester course groups
    trimester_groups = TrimesterCourseGroup.objects.all()
    if not trimester_groups.exists():
        return stats
    
    # Get all courses in these groups
    all_courses = []
    for group in trimester_groups:
        courses = list(group.courses.all())
        all_courses.extend(courses)
    
    # Get all students enrolled in these courses
    student_ids = CourseEnrollment.objects.filter(
        course__in=all_courses
    ).values_list('student_id', flat=True).distinct()
    
    stats['total_students'] = len(student_ids)
    
    # Process each student
    for student_id in student_ids:
        student = Student.objects.get(id=student_id)
        
        # Check for conflicts
        conflicts = get_trimester_course_conflicts(student)
        if conflicts:
            # Remove existing enrollments for these courses
            Enrollment.objects.filter(
                student=student,
                section__course__in=all_courses
            ).delete()
            
            # Try to reassign
            success, _, _ = assign_trimester_courses(student)
            if success:
                stats['conflicts_resolved'] += 1
        else:
            # Student already has valid assignments, but we'll check if we can balance better
            # Get student's current enrollments
            enrollments = Enrollment.objects.filter(
                student=student,
                section__course__in=all_courses
            ).select_related('section')
            
            # Check if we can move to less crowded sections
            current_period = enrollments.first().section.period_id if enrollments.exists() else None
            if current_period:
                # Get sections in this period for these courses
                current_sections = {e.section.id: e.section for e in enrollments}
                
                # Look for less crowded sections
                less_crowded_found = False
                for enrollment in enrollments:
                    course_id = enrollment.section.course_id
                    trimester = enrollment.section.when
                    current_count = enrollment.section.students.count()
                    
                    # Find alternative sections for this course and trimester
                    alt_sections = Section.objects.filter(
                        course_id=course_id,
                        when=trimester,
                        period_id=current_period
                    ).exclude(id=enrollment.section.id)
                    
                    for alt_section in alt_sections:
                        alt_count = alt_section.students.count()
                        if alt_count < current_count - 2:  # Only move if significant difference
                            # Move student to less crowded section
                            enrollment.section = alt_section
                            enrollment.save()
                            less_crowded_found = True
                            break
                
                if less_crowded_found:
                    stats['moved_students'] += 1
    
    return stats 