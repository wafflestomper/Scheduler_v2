from django.db.models import Count
from schedule.models import Student, Course, TrimesterCourseGroup, Period, Section, Enrollment, CourseEnrollment

def assign_trimester_courses(student, group_ids=None, preferred_period=None):
    """
    Assigns a student to trimester course sections based on constraints:
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
    # Get the trimester course groups for 6th grade if none provided
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
    
    # Get all available sections for these courses
    course_sections = Section.objects.filter(
        course__in=all_courses
    ).select_related('course', 'period')
    
    # Organize sections by period and trimester
    sections_by_period_trimester = {}
    for section in course_sections:
        period_id = section.period_id
        trimester = section.when
        
        if period_id not in sections_by_period_trimester:
            sections_by_period_trimester[period_id] = {}
        
        if trimester not in sections_by_period_trimester[period_id]:
            sections_by_period_trimester[period_id][trimester] = {}
        
        sections_by_period_trimester[period_id][trimester][section.course_id] = {
            'section': section,
            'current_enrollment': section.students.count(),
            'max_capacity': section.course.max_students
        }
    
    # Create lists to track assignments
    new_assignments = []
    
    # If student already has assignments
    if existing_assignments.exists():
        existing_period = None
        assigned_trimesters = {}
        assigned_courses = {}
        assigned_groups = {}
        
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
        
        # Complete missing assignments if possible
        if existing_period in sections_by_period_trimester:
            # Identify missing group assignments
            missing_groups = []
            for group in trimester_groups:
                if group.id not in assigned_groups:
                    missing_groups.append(group)
            
            available_trimesters = set(['t1', 't2', 't3']) - set(assigned_trimesters.keys())
            
            if len(missing_groups) == len(available_trimesters):
                # We can complete the assignment
                for group in missing_groups:
                    # Get the student's enrolled course for this group
                    enrolled_course = CourseEnrollment.objects.filter(
                        student=student,
                        course__in=group.courses.all()
                    ).first()
                    
                    if not enrolled_course:
                        continue
                    
                    course_id = enrolled_course.course.id
                    
                    # Find a section in an available trimester
                    for trimester in available_trimesters:
                        if (trimester in sections_by_period_trimester[existing_period] and 
                            course_id in sections_by_period_trimester[existing_period][trimester]):
                            section_data = sections_by_period_trimester[existing_period][trimester][course_id]
                            
                            if section_data['current_enrollment'] < section_data['max_capacity']:
                                # Create enrollment
                                enrollment = Enrollment.objects.create(
                                    student=student,
                                    section=section_data['section']
                                )
                                new_assignments.append(enrollment)
                                
                                # Mark this trimester as used
                                available_trimesters.remove(trimester)
                                break
                
                if len(new_assignments) == len(missing_groups):
                    return (True, "Completed partial assignments", new_assignments)
                else:
                    return (False, "Could not complete all assignments", new_assignments)
            else:
                return (False, "Mismatched missing groups and trimesters", new_assignments)
        else:
            return (False, "Existing period does not have required sections", new_assignments)
    
    # New assignment - find the best period
    valid_period_assignments = []
    
    # Gather student's enrolled courses for each group
    student_courses = []
    for group in trimester_groups:
        enrolled_course = CourseEnrollment.objects.filter(
            student=student,
            course__in=group.courses.all()
        ).first()
        
        if enrolled_course:
            student_courses.append(enrolled_course.course)
    
    # Calculate which periods have all required courses across different trimesters
    for period_id, trimesters in sections_by_period_trimester.items():
        # Check if all student's courses can be scheduled in this period
        all_courses_covered = True
        for course in student_courses:
            course_found = False
            for trimester, courses in trimesters.items():
                if course.id in courses:
                    course_found = True
                    break
            
            if not course_found:
                all_courses_covered = False
                break
        
        if all_courses_covered:
            valid_period_assignments.append(period_id)
    
    # Prioritize the preferred period if it's valid
    if preferred_period and preferred_period.id in valid_period_assignments:
        best_period = preferred_period.id
    else:
        # Find period with lowest maximum enrollment
        best_period = None
        lowest_max_enrollment = float('inf')
        
        for period_id in valid_period_assignments:
            # Calculate maximum enrollment across all sections for this period
            max_enrollment = 0
            valid_assignment = True
            
            for course in student_courses:
                course_found = False
                for trimester in ['t1', 't2', 't3']:
                    if (trimester in sections_by_period_trimester[period_id] and 
                        course.id in sections_by_period_trimester[period_id][trimester]):
                        section_data = sections_by_period_trimester[period_id][trimester][course.id]
                        if section_data['current_enrollment'] < section_data['max_capacity']:
                            course_found = True
                        max_enrollment = max(max_enrollment, section_data['current_enrollment'])
                
                if not course_found:
                    valid_assignment = False
            
            if valid_assignment and max_enrollment < lowest_max_enrollment:
                best_period = period_id
                lowest_max_enrollment = max_enrollment
    
    if best_period is None:
        return (False, "No period has available sections for all required courses", new_assignments)
    
    # Assign student to each course in a different trimester
    # Sort sections by enrollment to balance sections
    sorted_course_assignments = []
    for course in student_courses:
        for trimester in ['t1', 't2', 't3']:
            if (trimester in sections_by_period_trimester[best_period] and 
                course.id in sections_by_period_trimester[best_period][trimester]):
                section_data = sections_by_period_trimester[best_period][trimester][course.id]
                sorted_course_assignments.append((course.id, trimester, section_data))
    
    # Sort by enrollment (lowest first)
    sorted_course_assignments.sort(key=lambda x: x[2]['current_enrollment'])
    
    # Assign courses to trimesters
    assigned_trimesters = set()
    assigned_courses = set()
    
    for course_id, trimester, section_data in sorted_course_assignments:
        if (course_id not in assigned_courses and 
            trimester not in assigned_trimesters and 
            section_data['current_enrollment'] < section_data['max_capacity']):
            
            # Create enrollment
            enrollment = Enrollment.objects.create(
                student=student,
                section=section_data['section']
            )
            new_assignments.append(enrollment)
            
            assigned_trimesters.add(trimester)
            assigned_courses.add(course_id)
    
    if len(assigned_courses) == len(student_courses):
        return (True, "Successfully assigned all trimester courses", new_assignments)
    else:
        # Clean up partial assignments
        for enrollment in new_assignments:
            enrollment.delete()
        return (False, "Could not assign all required trimester courses", [])


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