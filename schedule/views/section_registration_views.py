import json
import random
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Count, Q, F
from schedule.models import Student, Course, Section, CourseEnrollment, Enrollment, Period, CourseGroup
from schedule.utils.language_course_utils import assign_language_courses, get_language_course_conflicts
from django.contrib import messages
from django.urls import reverse
from django import forms

def section_registration(request):
    """View for managing section registration for enrolled students"""
    print("DEBUG: section_registration view was called!")
    
    # Get all course enrollments that don't have section assignments
    unassigned_enrollments = CourseEnrollment.objects.filter(
        ~Q(student__sections__course=F('course'))
    ).select_related('student', 'course')
    
    # Count unique students with unassigned enrollments
    unassigned_students_count = unassigned_enrollments.values('student').distinct().count()
    
    # Get counts by course
    course_enrollment_stats = CourseEnrollment.objects.values('course__id', 'course__name') \
        .annotate(
            total_enrolled=Count('student', distinct=True),
            assigned_to_sections=Count('student', distinct=True, filter=Q(student__sections__course=F('course')))
        ).order_by('course__name')
    
    # Calculate students needing assignment
    for stats in course_enrollment_stats:
        stats['needing_assignment'] = stats['total_enrolled'] - stats['assigned_to_sections']
    
    # Get all sections with their capacities and current enrollment counts
    sections = Section.objects.all().select_related('course', 'period', 'teacher', 'room')
    section_stats = []
    
    for section in sections:
        enrolled_count = section.students.count()
        remaining_capacity = section.max_size - enrolled_count if section.max_size else None
        
        section_stats.append({
            'section': section,
            'enrolled_count': enrolled_count,
            'capacity': section.max_size,
            'remaining_capacity': remaining_capacity
        })
    
    context = {
        'unassigned_students_count': unassigned_students_count,
        'course_enrollment_stats': course_enrollment_stats,
        'section_stats': section_stats
    }
    
    return render(request, 'schedule/section_registration.html', context)

def assign_sections(request):
    """API endpoint to assign students to sections using constraint-based algorithm"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body) if request.body else {}
        course_id = data.get('course_id')  # Optional: assign for a specific course only
        
        # Call the new perfect balancing algorithm
        results = perfect_balance_assignment(course_id)
        
        return JsonResponse(results)
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def perfect_balance_assignment(course_id=None):
    """
    Completely rebalances sections by deregistering all students and 
    reassigning them optimally to achieve perfect balance
    """
    with transaction.atomic():
        # Prepare query for relevant courses
        course_query = Q()
        if course_id:
            course_query &= Q(id=course_id)
        
        # Get all courses that need section assignments
        courses = Course.objects.filter(course_query)
        
        if not courses.exists():
            return {
                'status': 'error',
                'message': 'No courses found for section assignment'
            }
        
        # Get all course groups for special scheduling
        course_groups = CourseGroup.objects.prefetch_related('courses').all()
        course_group_mappings = {}
        
        # Create mappings of courses to their groups for quick lookup
        for group in course_groups:
            for course in group.courses.all():
                course_group_mappings[course.id] = group
        
        # Tracking results
        assignments_count = 0
        failures_count = 0
        errors = []
        resolved_count = 0
        unresolved_count = 0
        
        # Process each course
        for course in courses:
            print(f"DEBUG: Processing course {course.name}")
            
            # Check if this course is part of a course group (for trimester/quarter courses)
            is_grouped_course = course.id in course_group_mappings
            course_group = course_group_mappings.get(course.id)
            
            # 1. Get all students enrolled in this course
            enrolled_students = CourseEnrollment.objects.filter(
                course=course
            ).select_related('student')
            
            if not enrolled_students.exists():
                print(f"DEBUG: No students enrolled in {course.name}")
                continue
            
            # 2. Get all sections for this course
            sections = Section.objects.filter(course=course).select_related('period')
            
            if not sections.exists():
                failures_count += enrolled_students.count()
                errors.append(f"No sections available for course {course.name}")
                continue
            
            # 3. Deregister all current section assignments for this course
            # This allows us to start fresh for optimal balancing
            current_enrollments = Enrollment.objects.filter(section__course=course)
            enrollment_count = current_enrollments.count()
            current_enrollments.delete()
            print(f"DEBUG: Deregistered {enrollment_count} existing enrollments for {course.name}")
            
            # 4. Initialize section data
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
            
            # 5. Calculate ideal distribution
            total_students = enrolled_students.count()
            num_sections = len(section_data)
            ideal_per_section = total_students / num_sections
            
            print(f"DEBUG: Course {course.name} - {total_students} students, {num_sections} sections, ideal: {ideal_per_section:.2f} per section")
            
            # 6. Sort students by a stable criterion (ID) to ensure consistent assignments
            students_to_assign = list(enrolled_students)
            students_to_assign.sort(key=lambda e: e.student.id)
            
            # 7. Special handling for grouped courses (trimester/quarter language courses)
            if is_grouped_course:
                print(f"DEBUG: Course {course.name} is part of group: {course_group.name}")
                
                # Get students who are enrolled in all courses in this group
                students_enrolled_in_all = []
                for student_enrollment in students_to_assign:
                    student = student_enrollment.student
                    # Count how many courses in this group the student is enrolled in
                    enrolled_count = CourseEnrollment.objects.filter(
                        student=student,
                        course__in=course_group.courses.all()
                    ).count()
                    
                    # If enrolled in all courses in the group, add to special handling list
                    if enrolled_count == course_group.courses.count():
                        students_enrolled_in_all.append(student_enrollment)
                
                print(f"DEBUG: {len(students_enrolled_in_all)} students are enrolled in all courses in this group")
                
                # Process these students separately
                for enrollment in students_enrolled_in_all:
                    student = enrollment.student
                    
                    # Find sections for each time segment (t1, t2, t3) with the same period
                    # Start by getting the student's current assignments in other courses of the group
                    student_group_assignments = {}
                    for group_course in course_group.courses.all():
                        if group_course.id == course.id:
                            continue  # Skip the current course
                        
                        # Check if student is already assigned to a section for this course
                        student_section_assignments = Enrollment.objects.filter(
                            student=student,
                            section__course=group_course
                        ).select_related('section')
                        
                        for assignment in student_section_assignments:
                            # Track the assigned period and trimester
                            student_group_assignments[assignment.section.when] = assignment.section.period_id
                    
                    # Determine which trimesters/quarters are already assigned
                    assigned_when_values = student_group_assignments.keys()
                    assigned_periods = list(student_group_assignments.values())
                    
                    # Find the appropriate section based on period and time segment
                    found_section = False
                    
                    # First check if student has existing assignments in the group
                    if assigned_periods:
                        # Try to find a section with the same period but different time segment
                        matching_period_sections = [
                            s for s in section_data 
                            if s['period_id'] in assigned_periods and 
                               s['when'] not in assigned_when_values and
                               s['current_enrollment'] < s['max_capacity']
                        ]
                        
                        if matching_period_sections:
                            # Choose the section with lowest enrollment
                            best_section = min(matching_period_sections, key=lambda s: s['current_enrollment'])
                            
                            # Create enrollment
                            Enrollment.objects.create(
                                student=student,
                                section=best_section['section']
                            )
                            
                            # Update section counts
                            best_section['current_enrollment'] += 1
                            assignments_count += 1
                            found_section = True
                            
                            print(f"DEBUG: Group scheduling - Assigned {student.name} to {course.name} section {best_section['section'].id} ({best_section['when']})")
                    
                    # If no matching section found or no existing assignments, find any available section
                    if not found_section:
                        # Find any section with capacity
                        available_sections = [s for s in section_data if s['current_enrollment'] < s['max_capacity']]
                        
                        if available_sections:
                            # Choose section with lowest enrollment
                            best_section = min(available_sections, key=lambda s: s['current_enrollment'])
                            
                            # Create enrollment
                            Enrollment.objects.create(
                                student=student,
                                section=best_section['section']
                            )
                            
                            # Update section counts
                            best_section['current_enrollment'] += 1
                            assignments_count += 1
                            
                            print(f"DEBUG: Group scheduling fallback - Assigned {student.name} to {course.name} section {best_section['section'].id} ({best_section['when']})")
                        else:
                            failures_count += 1
                            errors.append(f"No available sections for {student.name} in {course.name}")
                    
                    # Remove this student from the main assignment list
                    students_to_assign.remove(enrollment)
            
            # 8. First phase: Assign remaining students to sections to minimize the maximum enrollment
            student_schedule_conflicts = []
            
            for enrollment in students_to_assign:
                student = enrollment.student
                
                # Get student's current period assignments to avoid conflicts
                student_periods = Enrollment.objects.filter(
                    student=student,
                    section__period__isnull=False
                ).values_list('section__period_id', flat=True)
                
                # Find the eligible section with the lowest current enrollment
                eligible_sections = []
                for section_info in section_data:
                    # Skip sections that would create period conflicts
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
                
                print(f"DEBUG: Assigned {student.name} to section {best_section['section'].id}, now has {best_section['current_enrollment']} students")
            
            # 9. Handle students with schedule conflicts by trying alternate sections
            # We might need to break some constraints to assign all students
            for enrollment in student_schedule_conflicts:
                student = enrollment.student
                
                # First try sections with capacity available even if there are period conflicts
                capacity_sections = [s for s in section_data if s['current_enrollment'] < s['max_capacity']]
                
                if capacity_sections:
                    # Choose section with lowest enrollment
                    best_section = min(capacity_sections, key=lambda s: s['current_enrollment'])
                    
                    student_periods = Enrollment.objects.filter(
                        student=student,
                        section__period__isnull=False
                    ).values_list('section__period_id', flat=True)
                    
                    # Check if this will create a conflict
                    if best_section['period_id'] and best_section['period_id'] in student_periods:
                        # Find the conflicting enrollment
                        conflicting_enrollment = Enrollment.objects.get(
                            student=student,
                            section__period_id=best_section['period_id']
                        )
                        
                        # Error message
                        errors.append(f"Schedule conflict: {student.name} already has {conflicting_enrollment.section.course.name} " +
                                     f"during the same period as {course.name}")
                        unresolved_count += 1
                    
                    # Create enrollment record despite potential conflict
                    Enrollment.objects.create(
                        student=student,
                        section=best_section['section']
                    )
                    
                    # Update section counts
                    best_section['current_enrollment'] += 1
                    assignments_count += 1
                    resolved_count += 1
                    
                    print(f"DEBUG: Conflict resolution - Assigned {student.name} to section {best_section['section'].id}")
                else:
                    # All sections are at capacity
                    failures_count += 1
                    errors.append(f"All sections at capacity for {student.name} in {course.name}")
            
            # 10. Log final distribution
            print(f"DEBUG: Final distribution for {course.name}:")
            for section_info in section_data:
                print(f"  Section {section_info['section'].id}: {section_info['current_enrollment']} students")
        
        # Return combined results
        return {
            'status': 'success',
            'initial_assignments': assignments_count,
            'initial_failures': failures_count,
            'conflicts_resolved': resolved_count,
            'unresolvable_conflicts': unresolved_count,
            'message': f"Assigned {assignments_count} students to sections. " +
                      f"Resolved {resolved_count} conflicts. " +
                      f"{unresolved_count} conflicts could not be resolved.",
            'errors': errors
        }

def deregister_all_sections(request):
    """API endpoint to remove all students from their section assignments"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body) if request.body else {}
        course_id = data.get('course_id')  # Optional: deregister for a specific course only
        grade_level = data.get('grade_level')  # Optional: deregister for a specific grade only
        
        with transaction.atomic():
            # Build the query based on filters
            query = Q()
            
            if course_id:
                query &= Q(section__course_id=course_id)
            
            if grade_level:
                query &= Q(student__grade_level=grade_level)
            
            # Count enrollments before deletion for reporting
            enrollment_count = Enrollment.objects.filter(query).count()
            
            # Delete the enrollments
            Enrollment.objects.filter(query).delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Successfully deregistered {enrollment_count} section assignments',
                'deregistered_count': enrollment_count
            })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def assign_language_course_sections(request):
    """
    View for manually assigning language courses for students
    Ensures each student takes each language course in a different trimester
    but during the same period across all language courses.
    """
    if request.method == 'POST':
        form = LanguageCourseForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data['student']
            student = Student.objects.get(id=student_id)
            
            # Get selected courses and period
            language_courses = form.cleaned_data['courses']
            preferred_period = form.cleaned_data['preferred_period']
            
            # Perform the assignment
            success, message, assignments = assign_language_courses(student, language_courses, preferred_period)
            
            if success:
                messages.success(request, f"Successfully assigned language courses for {student.name}: {message}")
                # Redirect to student schedule view
                return redirect('view_student_schedule', student_id=student_id)
            else:
                messages.error(request, f"Error assigning language courses for {student.name}: {message}")
    else:
        form = LanguageCourseForm()
    
    # List students with language course conflicts
    students_with_conflicts = []
    
    # Get all students enrolled in language courses
    students = Student.objects.filter(
        courseenrollment__course__type='language'
    ).distinct()
    
    for student in students:
        conflicts = get_language_course_conflicts(student)
        if conflicts:
            students_with_conflicts.append({
                'student': student,
                'conflicts': conflicts
            })
    
    context = {
        'form': form,
        'students_with_conflicts': students_with_conflicts
    }
    
    return render(request, 'schedule/assign_language_courses.html', context)

class LanguageCourseForm(forms.Form):
    """Form for language course assignment"""
    student = forms.CharField(
        widget=forms.Select,
        label="Student"
    )
    courses = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label="Courses"
    )
    preferred_period = forms.CharField(
        widget=forms.Select,
        label="Preferred Period",
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get students who are enrolled in language courses
        self.fields['student'].widget.choices = [
            (s.id, s.name) for s in Student.objects.filter(
                courseenrollment__course__type='language'
            ).distinct().order_by('name')
        ]
        
        # Get language courses
        self.fields['courses'].choices = [
            (c.id, f"{c.name} - {c.id}") for c in Course.objects.filter(
                type='language'
            ).order_by('grade_level', 'name')
        ]
        
        # Get periods
        self.fields['preferred_period'].widget.choices = [
            ('', '-- No preference --')
        ] + [
            (p.id, str(p)) for p in Period.objects.all().order_by('slot')
        ] 