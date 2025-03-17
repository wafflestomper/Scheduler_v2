"""
Service class for handling language course registration operations.
"""
from django.db.models import Count
from django.db import transaction
from ...models import Student, Course, Period, Section, Enrollment, CourseEnrollment


class LanguageCourseService:
    """Service class for language course registration operations."""
    
    @staticmethod
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
            dict: Result with success flag, message, and assignments
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
        
        # If student already has assignments, clear them first
        if existing_assignments.exists():
            existing_assignments.delete()
        
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
            
            course_id = section.course_id
            sections_by_period_trimester[period_id][trimester][course_id] = section
        
        # Find a valid period that has all courses in different trimesters
        valid_periods = []
        
        for period_id, trimester_data in sections_by_period_trimester.items():
            # Skip if preferred_period is specified and this isn't it
            if preferred_period and period_id != preferred_period.id:
                continue
                
            # Check if this period has enough trimesters to work with
            if len(trimester_data) < len(language_courses):
                continue
            
            # Try to assign courses to different trimesters in this period
            valid_assignment = LanguageCourseService._find_valid_assignment(
                trimester_data, 
                language_courses
            )
            
            if valid_assignment:
                valid_periods.append({
                    'period_id': period_id,
                    'assignment': valid_assignment
                })
        
        # If no valid periods found, return failure
        if not valid_periods:
            return {
                'success': False,
                'message': f"Could not find a period with all required language courses in different trimesters",
                'assignments': []
            }
        
        # Choose the first valid period (or the preferred one if valid)
        chosen_period = valid_periods[0]
        
        # Create enrollments for the assignments
        assignments = []
        with transaction.atomic():
            for course_id, section in chosen_period['assignment'].items():
                enrollment = Enrollment.objects.create(
                    student=student,
                    section=section
                )
                assignments.append(enrollment)
        
        # Get the period name
        period = Period.objects.filter(id=chosen_period['period_id']).first()
        period_name = period.period_name if period else f"Period {chosen_period['period_id']}"
        
        return {
            'success': True,
            'message': f"Assigned to {len(assignments)} language courses in {period_name}",
            'assignments': assignments
        }
    
    @staticmethod
    def _find_valid_assignment(trimester_data, language_courses):
        """
        Find a valid assignment of courses to trimesters.
        
        Args:
            trimester_data: Dictionary of trimester -> course -> section
            language_courses: List of courses to assign
            
        Returns:
            dict or None: Dictionary of course_id -> section if valid assignment found, None otherwise
        """
        # Make a list of all course IDs
        course_ids = [course.id for course in language_courses]
        
        # Try to assign each course to a different trimester
        assignment = {}
        used_trimesters = set()
        
        for course_id in course_ids:
            assigned = False
            
            # Try each trimester
            for trimester, course_sections in trimester_data.items():
                # Skip if trimester already used
                if trimester in used_trimesters:
                    continue
                
                # Check if this course has a section in this trimester
                if course_id in course_sections:
                    section = course_sections[course_id]
                    assignment[course_id] = section
                    used_trimesters.add(trimester)
                    assigned = True
                    break
            
            # If this course couldn't be assigned, return failure
            if not assigned:
                return None
        
        return assignment
    
    @staticmethod
    def get_language_course_conflicts(student):
        """
        Check if a student has conflicts in their language course assignments.
        
        Args:
            student: The Student object to check
            
        Returns:
            list: List of conflict dictionaries with details
        """
        # Get language course assignments
        language_assignments = Enrollment.objects.filter(
            student=student,
            section__course__type='Language'
        ).select_related('section', 'section__course', 'section__period')
        
        if not language_assignments.exists():
            return []
        
        conflicts = []
        
        # Check if all are in the same period
        periods = set(a.section.period_id for a in language_assignments if a.section.period)
        if len(periods) > 1:
            periods_text = ", ".join(f"Period {p}" for p in periods)
            conflicts.append({
                'type': 'different_periods',
                'message': f"Language courses assigned to different periods: {periods_text}"
            })
        
        # Check if all are in different trimesters
        trimesters = {}
        for assignment in language_assignments:
            trimester = assignment.section.when
            if trimester in trimesters:
                conflicts.append({
                    'type': 'same_trimester',
                    'message': f"Multiple language courses assigned to {trimester}: {trimesters[trimester]} and {assignment.section.course.name}"
                })
            else:
                trimesters[trimester] = assignment.section.course.name
        
        return conflicts
    
    @staticmethod
    def balance_language_course_sections():
        """
        Balance enrollments across language course sections.
        
        Returns:
            dict: Result with success flag, message, and stats
        """
        # Get language sections
        language_sections = Section.objects.filter(
            course__type='Language'
        ).select_related('course', 'period')
        
        # Group by period and course
        sections_by_period_course = {}
        for section in language_sections:
            period_id = section.period_id if section.period else None
            course_id = section.course_id
            
            if period_id not in sections_by_period_course:
                sections_by_period_course[period_id] = {}
                
            if course_id not in sections_by_period_course[period_id]:
                sections_by_period_course[period_id][course_id] = []
                
            sections_by_period_course[period_id][course_id].append(section)
        
        # For each period and course, balance enrollments
        changes_made = 0
        with transaction.atomic():
            for period_id, courses in sections_by_period_course.items():
                for course_id, sections in courses.items():
                    # Skip if there's only one section
                    if len(sections) <= 1:
                        continue
                        
                    # Get enrollment counts
                    section_enrollments = {}
                    total_enrollments = 0
                    
                    for section in sections:
                        enrollment_count = section.students.count()
                        section_enrollments[section.id] = {
                            'section': section,
                            'count': enrollment_count
                        }
                        total_enrollments += enrollment_count
                    
                    # Calculate target size (even distribution)
                    target_size = total_enrollments // len(sections)
                    
                    # Balance sections
                    overloaded_sections = []
                    underloaded_sections = []
                    
                    for section_id, data in section_enrollments.items():
                        if data['count'] > target_size + 1:
                            # This section has more than target + 1 students
                            overloaded_sections.append({
                                'section': data['section'],
                                'count': data['count'],
                                'excess': data['count'] - target_size
                            })
                        elif data['count'] < target_size:
                            # This section has fewer than target students
                            underloaded_sections.append({
                                'section': data['section'],
                                'count': data['count'],
                                'needed': target_size - data['count']
                            })
                    
                    # Move students from overloaded to underloaded sections
                    for overloaded in overloaded_sections:
                        for underloaded in underloaded_sections:
                            # Skip if underloaded section is now at target
                            if underloaded['needed'] <= 0:
                                continue
                                
                            # Skip if overloaded section has no more excess
                            if overloaded['excess'] <= 0:
                                break
                                
                            # Calculate how many students to move
                            to_move = min(overloaded['excess'], underloaded['needed'])
                            
                            if to_move > 0:
                                # Get students to move
                                students_to_move = Enrollment.objects.filter(
                                    section=overloaded['section']
                                ).select_related('student')[:to_move]
                                
                                # Move each student
                                for enrollment in students_to_move:
                                    student = enrollment.student
                                    
                                    # Delete the old enrollment
                                    enrollment.delete()
                                    
                                    # Create a new enrollment
                                    Enrollment.objects.create(
                                        student=student,
                                        section=underloaded['section']
                                    )
                                    
                                    changes_made += 1
                                
                                # Update counts
                                overloaded['excess'] -= to_move
                                underloaded['needed'] -= to_move
        
        return {
            'success': True,
            'message': f"Balanced language course sections with {changes_made} student reassignments",
            'changes_made': changes_made
        } 