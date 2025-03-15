import json
import random
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Count, Q, F
from schedule.models import Student, Course, Section, CourseEnrollment, Enrollment, Period

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
        
        # Phase 1: Initial assignment without conflict resolution
        assignment_results = initial_assignment_phase(course_id)
        
        # Phase 2: Conflict resolution
        conflict_resolution_results = conflict_resolution_phase(assignment_results)
        
        # Combine results
        results = {
            'status': 'success',
            'initial_assignments': assignment_results['assignments_count'],
            'initial_failures': assignment_results['failures_count'],
            'conflicts_resolved': conflict_resolution_results['resolved_count'],
            'unresolvable_conflicts': conflict_resolution_results['unresolved_count'],
            'message': f"Assigned {assignment_results['assignments_count']} students to sections. " +
                      f"Resolved {conflict_resolution_results['resolved_count']} conflicts. " +
                      f"{conflict_resolution_results['unresolved_count']} conflicts could not be resolved.",
            'errors': assignment_results['errors'] + conflict_resolution_results['errors']
        }
        
        return JsonResponse(results)
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def initial_assignment_phase(course_id=None):
    """
    Phase 1: Initial assignment of students to sections
    Distributes students randomly to sections respecting capacity constraints
    """
    with transaction.atomic():
        # Get all course enrollments that don't have section assignments
        unassigned_query = ~Q(student__sections__course=F('course'))
        if course_id:
            unassigned_enrollments = CourseEnrollment.objects.filter(
                unassigned_query,
                course_id=course_id
            ).select_related('student', 'course')
        else:
            unassigned_enrollments = CourseEnrollment.objects.filter(
                unassigned_query
            ).select_related('student', 'course')
        
        # Group by course
        enrollments_by_course = {}
        for enrollment in unassigned_enrollments:
            if enrollment.course_id not in enrollments_by_course:
                enrollments_by_course[enrollment.course_id] = []
            enrollments_by_course[enrollment.course_id].append(enrollment)
        
        # Tracking results
        assignments_count = 0
        failures_count = 0
        errors = []
        
        # Process each course
        for course_id, enrollments in enrollments_by_course.items():
            # Get available sections for this course
            sections = Section.objects.filter(course_id=course_id).select_related('period')
            
            if not sections.exists():
                failures_count += len(enrollments)
                errors.append(f"No sections available for course {enrollments[0].course.name}")
                continue
            
            # Calculate available capacity for each section
            section_capacities = {}
            for section in sections:
                enrolled_count = section.students.count()
                max_capacity = section.max_size if section.max_size else float('inf')
                available = max_capacity - enrolled_count
                
                section_capacities[section.id] = {
                    'section': section,
                    'available': available,
                    'period_id': section.period_id if section.period else None
                }
            
            # Randomize student order
            random.shuffle(enrollments)
            
            # Assign students to sections
            for enrollment in enrollments:
                student = enrollment.student
                
                # Sort sections by available capacity (descending)
                available_sections = sorted(
                    [s for s in section_capacities.values() if s['available'] > 0],
                    key=lambda x: x['available'],
                    reverse=True
                )
                
                if not available_sections:
                    failures_count += 1
                    errors.append(f"No available capacity in any section for {student.name} in {enrollment.course.name}")
                    continue
                
                # Assign to the section with most available capacity
                best_section = available_sections[0]['section']
                
                # Create enrollment record
                Enrollment.objects.create(
                    student=student,
                    section=best_section
                )
                
                # Update available capacity
                section_capacities[best_section.id]['available'] -= 1
                assignments_count += 1
        
        return {
            'assignments_count': assignments_count,
            'failures_count': failures_count,
            'errors': errors
        }

def conflict_resolution_phase(initial_results):
    """
    Phase 2: Resolve schedule conflicts
    Checks for and resolves situations where students are assigned to multiple sections in the same period
    """
    # Get all students with section assignments
    students_with_sections = Student.objects.filter(
        sections__isnull=False
    ).distinct()
    
    resolved_count = 0
    unresolved_count = 0
    errors = []
    
    with transaction.atomic():
        for student in students_with_sections:
            # Get all the student's section assignments by period
            sections_by_period = {}
            
            for enrollment in Enrollment.objects.filter(student=student).select_related('section__period', 'section__course'):
                section = enrollment.section
                if not section.period:
                    continue
                    
                period_id = section.period_id
                if period_id not in sections_by_period:
                    sections_by_period[period_id] = []
                sections_by_period[period_id].append(enrollment)
            
            # Check for conflicts (more than one section per period)
            for period_id, enrollments in sections_by_period.items():
                if len(enrollments) <= 1:
                    continue
                
                # We have a conflict in this period
                # Sort by course priority (for now, we'll use alphabetical order as placeholder)
                sorted_enrollments = sorted(
                    enrollments,
                    key=lambda e: e.section.course.name
                )
                
                # Keep only the first enrollment, remove the rest
                keep_enrollment = sorted_enrollments[0]
                conflict_enrollments = sorted_enrollments[1:]
                
                for enrollment in conflict_enrollments:
                    # Try to find an alternative section for this course
                    alternate_section = find_alternate_section(student, enrollment.section.course, exclude_period=period_id)
                    
                    if alternate_section:
                        # Move to alternate section
                        enrollment.section = alternate_section
                        enrollment.save()
                        resolved_count += 1
                    else:
                        # No alternate section available, remove this enrollment
                        enrollment.delete()
                        unresolved_count += 1
                        errors.append(f"Removed conflicting enrollment for {student.name} in {enrollment.section.course.name} " +
                                      f"during period {Period.objects.get(id=period_id).name}")
    
    return {
        'resolved_count': resolved_count,
        'unresolved_count': unresolved_count,
        'errors': errors
    }

def find_alternate_section(student, course, exclude_period=None):
    """Find an alternate section for a student in a different period"""
    # Get all the student's current period assignments
    student_periods = Enrollment.objects.filter(
        student=student,
        section__period__isnull=False
    ).values_list('section__period_id', flat=True)
    
    # Find sections for this course that don't conflict with the student's schedule
    query = Q(course=course)
    
    if exclude_period:
        query &= ~Q(period_id=exclude_period)
    
    if student_periods:
        query &= ~Q(period_id__in=student_periods)
    
    # Also check capacity constraints
    available_sections = []
    for section in Section.objects.filter(query):
        if section.max_size is None or section.students.count() < section.max_size:
            available_sections.append(section)
    
    if available_sections:
        # Randomize selection among available sections
        return random.choice(available_sections)
    
    return None

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