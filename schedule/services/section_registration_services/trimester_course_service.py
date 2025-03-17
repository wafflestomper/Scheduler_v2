"""
Service class for handling trimester course registration operations.
"""
from django.db.models import Count
from django.db import transaction
from ...models import Student, Course, Period, Section, Enrollment, CourseEnrollment, TrimesterCourseGroup


class TrimesterCourseService:
    """Service class for trimester course registration operations."""
    
    @staticmethod
    def assign_trimester_courses(student, group_ids, preferred_period=None):
        """
        Assigns a student to one course from each trimester course group in different trimesters
        but during the same period.
        
        Args:
            student: The Student object to assign
            group_ids: List of trimester course group IDs
            preferred_period: Optional preferred Period object
            
        Returns:
            dict: Result with success flag, message, and assignments
        """
        # Get the trimester course groups
        groups = TrimesterCourseGroup.objects.filter(id__in=group_ids).prefetch_related('courses')
        
        if not groups:
            return {
                'success': False,
                'message': "No valid trimester course groups specified",
                'assignments': []
            }
        
        # Get all courses from these groups
        all_courses = []
        for group in groups:
            all_courses.extend(list(group.courses.all()))
        
        # Ensure student is enrolled in these courses
        for course in all_courses:
            CourseEnrollment.objects.get_or_create(student=student, course=course)
        
        # Clear any existing assignments for these courses
        existing_assignments = Enrollment.objects.filter(
            student=student,
            section__course__in=all_courses
        )
        if existing_assignments.exists():
            existing_assignments.delete()
        
        # Get all sections for these courses
        sections = Section.objects.filter(
            course__in=all_courses
        ).select_related('course', 'period')
        
        # Organize sections by period, trimester, and group
        sections_by_period = {}
        for section in sections:
            period_id = section.period_id if section.period else None
            if not period_id:
                continue  # Skip sections without a period
                
            trimester = section.when
            course_id = section.course_id
            
            # Determine which group this course belongs to
            group_id = None
            for group in groups:
                if course_id in [c.id for c in group.courses.all()]:
                    group_id = group.id
                    break
                    
            if not group_id:
                continue  # Skip sections for courses not in requested groups
            
            # Initialize nested dictionaries if needed
            if period_id not in sections_by_period:
                sections_by_period[period_id] = {'trimesters': {}}
                
            if trimester not in sections_by_period[period_id]['trimesters']:
                sections_by_period[period_id]['trimesters'][trimester] = {}
                
            if group_id not in sections_by_period[period_id]['trimesters'][trimester]:
                sections_by_period[period_id]['trimesters'][trimester][group_id] = []
                
            sections_by_period[period_id]['trimesters'][trimester][group_id].append(section)
        
        # Find a valid assignment
        valid_assignments = []
        
        # Check each period
        for period_id, period_data in sections_by_period.items():
            # Skip if preferred_period specified and this isn't it
            if preferred_period and period_id != preferred_period.id:
                continue
                
            trimesters = period_data['trimesters']
            
            # Try to assign one course from each group to a different trimester
            assignment = TrimesterCourseService._find_valid_assignment(trimesters, groups)
            
            if assignment:
                valid_assignments.append({
                    'period_id': period_id,
                    'assignment': assignment
                })
        
        # If no valid assignments found, return failure
        if not valid_assignments:
            return {
                'success': False,
                'message': "Could not find a valid assignment with one course from each group in different trimesters",
                'assignments': []
            }
        
        # Choose the first valid assignment (or the preferred one if valid)
        chosen_assignment = valid_assignments[0]
        
        # Create enrollments for the assigned sections
        assignments = []
        with transaction.atomic():
            for section in chosen_assignment['assignment']:
                enrollment = Enrollment.objects.create(
                    student=student,
                    section=section
                )
                assignments.append(enrollment)
        
        # Get the period name
        period = Period.objects.filter(id=chosen_assignment['period_id']).first()
        period_name = period.period_name if period else f"Period {chosen_assignment['period_id']}"
        
        return {
            'success': True,
            'message': f"Assigned {len(assignments)} courses from different groups in {period_name}",
            'assignments': assignments
        }
    
    @staticmethod
    def _find_valid_assignment(trimesters, groups):
        """
        Find a valid assignment with one course from each group in different trimesters.
        
        Args:
            trimesters: Dictionary of trimester -> group_id -> sections
            groups: List of TrimesterCourseGroup objects
            
        Returns:
            list or None: List of sections if valid assignment found, None otherwise
        """
        # Create a list of all group IDs
        group_ids = [group.id for group in groups]
        
        # Try all permutations of trimester assignments
        trimester_names = list(trimesters.keys())
        
        # If there aren't enough trimesters, fail
        if len(trimester_names) < len(group_ids):
            return None
        
        # Try to assign each group to a different trimester
        assignment = []
        used_trimesters = set()
        
        for group_id in group_ids:
            assigned = False
            
            # Try each trimester
            for trimester in trimester_names:
                # Skip if trimester already used
                if trimester in used_trimesters:
                    continue
                
                # Check if this group has sections in this trimester
                if trimester in trimesters and group_id in trimesters[trimester]:
                    # Use the first available section
                    if trimesters[trimester][group_id]:
                        section = trimesters[trimester][group_id][0]
                        assignment.append(section)
                        used_trimesters.add(trimester)
                        assigned = True
                        break
            
            # If this group couldn't be assigned, return failure
            if not assigned:
                return None
        
        return assignment
    
    @staticmethod
    def get_trimester_course_conflicts(student):
        """
        Check if a student has conflicts in their trimester course assignments.
        
        Args:
            student: The Student object to check
            
        Returns:
            list: List of conflict dictionaries with details
        """
        # Get all trimester groups and their courses
        trimester_groups = TrimesterCourseGroup.objects.all().prefetch_related('courses')
        
        # Create a map of course IDs to group IDs
        course_to_group = {}
        for group in trimester_groups:
            for course in group.courses.all():
                course_to_group[course.id] = group.id
        
        # Get all trimester course assignments
        trimester_assignments = Enrollment.objects.filter(
            student=student,
            section__course__id__in=course_to_group.keys()
        ).select_related('section', 'section__course', 'section__period')
        
        if not trimester_assignments.exists():
            return []
        
        conflicts = []
        
        # Check if all courses from the same group are assigned
        assignments_by_group = {}
        for assignment in trimester_assignments:
            course_id = assignment.section.course_id
            group_id = course_to_group.get(course_id)
            
            if group_id not in assignments_by_group:
                assignments_by_group[group_id] = []
                
            assignments_by_group[group_id].append(assignment)
        
        # Check if multiple courses from the same group are assigned
        for group_id, assignments in assignments_by_group.items():
            if len(assignments) > 1:
                course_names = [a.section.course.name for a in assignments]
                conflicts.append({
                    'type': 'multiple_courses_same_group',
                    'message': f"Multiple courses from the same group {group_id} assigned: {', '.join(course_names)}"
                })
        
        # Check if all assignments have the same period
        periods = set(a.section.period_id for a in trimester_assignments if a.section.period)
        if len(periods) > 1:
            conflicts.append({
                'type': 'different_periods',
                'message': f"Trimester courses assigned to different periods: {', '.join(f'Period {p}' for p in periods)}"
            })
        
        # Check if courses are in different trimesters
        trimesters = {}
        for assignment in trimester_assignments:
            trimester = assignment.section.when
            if trimester in trimesters:
                conflicts.append({
                    'type': 'same_trimester',
                    'message': f"Multiple trimester courses assigned to {trimester}: {trimesters[trimester]} and {assignment.section.course.name}"
                })
            else:
                trimesters[trimester] = assignment.section.course.name
        
        return conflicts
    
    @staticmethod
    def balance_trimester_courses():
        """
        Balance enrollments across trimester course sections.
        
        Returns:
            dict: Result with success flag, message, and changes made
        """
        # Get all trimester groups and their courses
        trimester_groups = TrimesterCourseGroup.objects.all().prefetch_related('courses')
        
        # Create a list of all trimester course IDs
        all_trimester_course_ids = []
        for group in trimester_groups:
            all_trimester_course_ids.extend([c.id for c in group.courses.all()])
        
        # Get all sections for these courses
        sections = Section.objects.filter(
            course__id__in=all_trimester_course_ids
        ).select_related('course', 'period')
        
        # Group by period, trimester, and course
        sections_by_period_trimester_course = {}
        for section in sections:
            period_id = section.period_id if section.period else None
            trimester = section.when
            course_id = section.course_id
            
            if period_id not in sections_by_period_trimester_course:
                sections_by_period_trimester_course[period_id] = {}
                
            if trimester not in sections_by_period_trimester_course[period_id]:
                sections_by_period_trimester_course[period_id][trimester] = {}
                
            if course_id not in sections_by_period_trimester_course[period_id][trimester]:
                sections_by_period_trimester_course[period_id][trimester][course_id] = []
                
            sections_by_period_trimester_course[period_id][trimester][course_id].append(section)
        
        # Balance enrollments
        changes_made = 0
        with transaction.atomic():
            for period_id, trimester_data in sections_by_period_trimester_course.items():
                for trimester, course_data in trimester_data.items():
                    for course_id, section_list in course_data.items():
                        # Skip if only one section
                        if len(section_list) <= 1:
                            continue
                            
                        # Get enrollment counts
                        section_enrollments = {}
                        total_enrollments = 0
                        
                        for section in section_list:
                            enrollment_count = section.students.count()
                            section_enrollments[section.id] = {
                                'section': section,
                                'count': enrollment_count
                            }
                            total_enrollments += enrollment_count
                        
                        # Calculate target size (even distribution)
                        target_size = total_enrollments // len(section_list)
                        
                        # Balance sections
                        changes_made += TrimesterCourseService._balance_sections(
                            section_enrollments, 
                            target_size
                        )
        
        return {
            'success': True,
            'message': f"Balanced trimester course sections with {changes_made} student reassignments",
            'changes_made': changes_made
        }
    
    @staticmethod
    def _balance_sections(section_enrollments, target_size):
        """
        Balance enrollments across sections of a course.
        
        Args:
            section_enrollments: Dictionary of section_id -> {section, count}
            target_size: Target enrollment size for each section
            
        Returns:
            int: Number of changes made
        """
        # Identify overloaded and underloaded sections
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
        changes_made = 0
        
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
        
        return changes_made 