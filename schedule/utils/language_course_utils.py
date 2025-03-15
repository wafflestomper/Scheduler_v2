from django.db.models import Count
from schedule.models import Student, Course, CourseGroup, Period, Section, Enrollment, CourseEnrollment

def assign_language_courses(student, language_courses=None, preferred_period=None):
    """
    Assigns a student to language course sections based on constraints:
    - Each language course in a different trimester
    - All language courses in the same period
    
    Args:
        student: The Student object to assign
        language_courses: Optional list of Course objects (defaults to SPA6, CHI6, FRE6)
        preferred_period: Optional preferred Period object
        
    Returns:
        tuple: (success, message, assignments)
            - success: Boolean indicating if assignment was successful
            - message: Status message
            - assignments: List of created Enrollment objects
    """
    # Default to 6th grade language courses if none provided
    if language_courses is None:
        language_courses = Course.objects.filter(id__in=['SPA6', 'CHI6', 'FRE6'])
    
    # Ensure student is enrolled in these courses
    for course in language_courses:
        CourseEnrollment.objects.get_or_create(student=student, course=course)
    
    # Check if student already has any language section assignments
    existing_assignments = Enrollment.objects.filter(
        student=student,
        section__course__in=language_courses
    ).select_related('section', 'section__course', 'section__period')
    
    # Get all available sections for these courses
    course_sections = Section.objects.filter(
        course__in=language_courses
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
    
    # Find or create a CourseGroup for these language courses
    group_name = f"Language Courses - Grade {student.grade_level}"
    language_group, _ = CourseGroup.objects.get_or_create(
        name=group_name,
        defaults={'description': f"Group for grade {student.grade_level} language courses"}
    )
    
    # Add courses to group if needed
    for course in language_courses:
        language_group.courses.add(course)
    
    # If preferred period is provided, set it on the course group
    if preferred_period:
        language_group.preferred_period = preferred_period
        language_group.save()
    
    # Create lists to track assignments
    new_assignments = []
    
    # If student already has assignments
    if existing_assignments.exists():
        existing_period = None
        assigned_trimesters = {}
        assigned_courses = {}
        
        for enrollment in existing_assignments:
            section = enrollment.section
            course_id = section.course_id
            trimester = section.when
            period_id = section.period_id
            
            assigned_courses[course_id] = {
                'section': section,
                'trimester': trimester,
                'period': period_id
            }
            
            if existing_period is None:
                existing_period = period_id
            elif existing_period != period_id:
                return (False, f"Student has language courses in different periods", new_assignments)
            
            assigned_trimesters[trimester] = course_id
        
        # Complete missing assignments if possible
        if existing_period in sections_by_period_trimester:
            missing_courses = set([c.id for c in language_courses]) - set(assigned_courses.keys())
            available_trimesters = set(['t1', 't2', 't3']) - set(assigned_trimesters.keys())
            
            if len(missing_courses) == len(available_trimesters):
                # We can complete the assignment
                for course_id in missing_courses:
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
                
                if len(new_assignments) == len(missing_courses):
                    return (True, "Completed partial assignments", new_assignments)
                else:
                    return (False, "Could not complete all assignments", new_assignments)
            else:
                return (False, "Mismatched missing courses and trimesters", new_assignments)
        else:
            return (False, "Existing period does not have required sections", new_assignments)
    
    # New assignment - find the best period
    valid_period_assignments = []
    
    # Calculate which periods have all required courses across different trimesters
    for period_id, trimesters in sections_by_period_trimester.items():
        all_courses_covered = set()
        for trimester, courses in trimesters.items():
            all_courses_covered.update(courses.keys())
        
        if len(all_courses_covered) == len(language_courses):
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
            
            for trimester in ['t1', 't2', 't3']:
                if trimester in sections_by_period_trimester[period_id]:
                    for course in language_courses:
                        course_id = course.id
                        if course_id in sections_by_period_trimester[period_id][trimester]:
                            section_data = sections_by_period_trimester[period_id][trimester][course_id]
                            if section_data['current_enrollment'] >= section_data['max_capacity']:
                                valid_assignment = False
                            max_enrollment = max(max_enrollment, section_data['current_enrollment'])
            
            if valid_assignment and max_enrollment < lowest_max_enrollment:
                best_period = period_id
                lowest_max_enrollment = max_enrollment
    
    if best_period is None:
        return (False, "No period has available sections for all required courses", new_assignments)
    
    # Assign student to each language course in a different trimester
    # Sort courses by enrollment to balance sections
    sorted_course_assignments = []
    for course in language_courses:
        course_id = course.id
        for trimester in ['t1', 't2', 't3']:
            if (trimester in sections_by_period_trimester[best_period] and 
                course_id in sections_by_period_trimester[best_period][trimester]):
                section_data = sections_by_period_trimester[best_period][trimester][course_id]
                sorted_course_assignments.append((course_id, trimester, section_data))
    
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
    
    if len(assigned_courses) == len(language_courses):
        return (True, "Successfully assigned all language courses", new_assignments)
    else:
        # Clean up partial assignments
        for enrollment in new_assignments:
            enrollment.delete()
        return (False, "Could not assign all required language courses", [])


def get_language_course_conflicts(student):
    """
    Check for conflicts in a student's language course assignments
    
    Args:
        student: The Student object to check
        
    Returns:
        list: List of conflict messages
    """
    conflicts = []
    
    # Get language courses for this student's grade level
    language_courses = Course.objects.filter(
        type='language', 
        grade_level=student.grade_level
    )
    
    # Get student's language section assignments
    enrollments = Enrollment.objects.filter(
        student=student,
        section__course__in=language_courses
    ).select_related('section', 'section__course', 'section__period')
    
    if not enrollments.exists():
        return conflicts
    
    # Check for period consistency
    periods = set()
    for enrollment in enrollments:
        periods.add(enrollment.section.period_id)
    
    if len(periods) > 1:
        conflicts.append("Student is assigned to language courses in different periods")
    
    # Check for trimester conflicts
    trimesters = {}
    for enrollment in enrollments:
        trimester = enrollment.section.when
        if trimester in trimesters:
            conflicts.append(f"Student has multiple language courses in trimester {trimester}")
        trimesters[trimester] = enrollment.section.course.name
    
    return conflicts


def balance_language_course_sections():
    """
    Balance enrollments across language course sections
    
    Returns:
        dict: Statistics about the balancing operation
    """
    stats = {
        'courses_processed': 0,
        'students_moved': 0,
        'sections_balanced': 0
    }
    
    # Get language courses
    language_courses = Course.objects.filter(type='language')
    stats['courses_processed'] = language_courses.count()
    
    # Process each course
    for course in language_courses:
        # Get sections for this course
        sections = Section.objects.filter(course=course).annotate(
            student_count=Count('students')
        ).order_by('student_count')
        
        if sections.count() < 2:
            continue  # Need at least 2 sections to balance
        
        # Calculate average enrollment
        total_students = sum(section.student_count for section in sections)
        avg_students = total_students / sections.count()
        
        # Find sections that are significantly over/under enrolled
        over_enrolled = []
        under_enrolled = []
        
        for section in sections:
            if section.student_count > avg_students + 2:
                over_enrolled.append(section)
            elif section.student_count < avg_students - 2:
                under_enrolled.append(section)
        
        # Balance by moving students from over-enrolled to under-enrolled
        for source_section in over_enrolled:
            if not under_enrolled:
                break
                
            target_section = under_enrolled[0]
            
            # Find students in the source section that could be moved
            source_enrollments = Enrollment.objects.filter(
                section=source_section
            ).select_related('student')
            
            for enrollment in source_enrollments:
                student = enrollment.student
                
                # Check if moving would disrupt the student's language course scheduling
                can_move = True
                
                # Get student's other language course assignments
                other_language_enrollments = Enrollment.objects.filter(
                    student=student,
                    section__course__type='language'
                ).exclude(section=source_section)
                
                if other_language_enrollments.exists():
                    # If student has other language courses, they must all be in the same period
                    for other_enrollment in other_language_enrollments:
                        if other_enrollment.section.period_id != target_section.period_id:
                            can_move = False
                            break
                
                if can_move:
                    # Move the student
                    enrollment.section = target_section
                    enrollment.save()
                    stats['students_moved'] += 1
                    
                    # Update section counts
                    source_section.student_count -= 1
                    target_section.student_count += 1
                    
                    # If target section is no longer under-enrolled, remove it
                    if target_section.student_count >= avg_students - 2:
                        under_enrolled.pop(0)
                        stats['sections_balanced'] += 1
                        if not under_enrolled:
                            break
    
    return stats 