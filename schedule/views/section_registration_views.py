import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages

from schedule.models import Student, Section, Course, CourseEnrollment, Enrollment, TrimesterCourseGroup
from schedule.forms import LanguageCourseForm, TrimesterCourseForm
from schedule.utils.section_registration_utils import (
    get_section_stats, get_course_enrollment_stats,
    get_unassigned_students_count, deregister_sections, clear_student_enrollments
)
from schedule.utils.balance_assignment import perfect_balance_assignment
from schedule.utils.language_course_utils import assign_language_courses, get_language_course_conflicts
from schedule.utils.trimester_course_utils import assign_trimester_courses, get_trimester_course_conflicts

def registration_home(request):
    """
    Home page for the section registration system showing registration stats.
    """
    # Get all sections with their capacities and current enrollment counts
    sections = Section.objects.all().select_related('course', 'period', 'teacher', 'room')
    section_stats = get_section_stats(sections)
    
    # Get course enrollment statistics
    course_enrollment_stats = get_course_enrollment_stats()
    
    # Get count of students with unassigned sections
    unassigned_students_count = get_unassigned_students_count()
    
    context = {
        'unassigned_students_count': unassigned_students_count,
        'course_enrollment_stats': course_enrollment_stats,
        'section_stats': section_stats
    }
    
    return render(request, 'schedule/section_registration.html', context)

def view_student_schedule(request, student_id):
    """
    View a specific student's schedule
    """
    student = Student.objects.get(id=student_id)
    
    # Get the student's current section assignments
    enrollments = Enrollment.objects.filter(
        student=student
    ).select_related('section', 'section__course', 'section__period', 'section__teacher', 'section__room')
    
    # Get courses the student is enrolled in but not assigned to sections
    enrolled_course_ids = [enrollment.section.course.id for enrollment in enrollments]
    unassigned_courses = CourseEnrollment.objects.filter(
        student=student
    ).exclude(
        course__id__in=enrolled_course_ids
    ).select_related('course')
    
    context = {
        'student': student,
        'enrollments': enrollments,
        'unassigned_courses': unassigned_courses
    }
    
    return render(request, 'schedule/student_schedule.html', context)

def section_registration(request):
    """
    API view for managing section registration actions via AJAX.
    Handles various actions like assigning sections and deregistering enrollments.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            action = data.get('action')
            
            if action == 'assign_sections':
                course_id = data.get('course_id')  # Optional: assign for a specific course only
                # Call the balancing algorithm
                results = perfect_balance_assignment(course_id)
                return JsonResponse(results)
                
            elif action == 'deregister_all_sections':
                course_id = data.get('course_id')  # Optional: deregister for a specific course only
                grade_level = data.get('grade_level')  # Optional: deregister for a specific grade only
                
                # Deregister the sections
                enrollment_count = deregister_sections(course_id, grade_level)
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Successfully deregistered {enrollment_count} section assignments',
                    'deregistered_count': enrollment_count
                })
                
            elif action == 'clear_student_enrollments':
                student_id = data.get('student_id')
                
                if not student_id:
                    return JsonResponse({'status': 'error', 'message': 'Student ID is required'})
                
                # Clear the student's enrollments
                enrollment_count = clear_student_enrollments(student_id)
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Successfully cleared {enrollment_count} section enrollments for student',
                    'cleared_count': enrollment_count
                })
                
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid action'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    # For non-POST requests, redirect to the registration home page
    return redirect('registration_home')

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
        course_enrollments__course__type='language'
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

def assign_trimester_course_sections(request):
    """
    View for manually assigning trimester courses for 6th grade students
    Ensures each student takes one course from each group in a different trimester
    but during the same period.
    """
    if request.method == 'POST':
        form = TrimesterCourseForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data['student']
            student = Student.objects.get(id=student_id)
            
            # Get selected groups and period
            group_ids = form.cleaned_data['group_selections']
            preferred_period_id = form.cleaned_data['preferred_period']
            
            preferred_period = None
            if preferred_period_id:
                from schedule.models import Period
                preferred_period = Period.objects.get(id=preferred_period_id)
            
            # Perform the assignment
            success, message, assignments = assign_trimester_courses(student, group_ids, preferred_period)
            
            if success:
                messages.success(request, f"Successfully assigned trimester courses for {student.name}: {message}")
                # Redirect to student schedule view
                return redirect('view_student_schedule', student_id=student_id)
            else:
                messages.error(request, f"Error assigning trimester courses for {student.name}: {message}")
    else:
        form = TrimesterCourseForm()
    
    # List students with trimester course conflicts
    students_with_conflicts = []
    
    # Get all 6th grade students
    students = Student.objects.filter(grade_level=6).distinct()
    
    # Get all trimester course groups
    trimester_groups = TrimesterCourseGroup.objects.all().prefetch_related('courses')
    all_trimester_courses = []
    for group in trimester_groups:
        all_trimester_courses.extend(list(group.courses.all()))
    
    # Filter students to only those enrolled in trimester courses
    enrolled_student_ids = CourseEnrollment.objects.filter(
        course__in=all_trimester_courses
    ).values_list('student_id', flat=True).distinct()
    
    students = students.filter(id__in=enrolled_student_ids)
    
    # Check for conflicts
    for student in students:
        conflicts = get_trimester_course_conflicts(student)
        if conflicts:
            students_with_conflicts.append({
                'student': student,
                'conflicts': conflicts
            })
    
    # Get configuration summary
    group_summary = []
    for group in trimester_groups:
        courses = [c.id for c in group.courses.all()]
        group_summary.append({
            'name': group.name,
            'type': group.get_group_type_display(),
            'courses': courses
        })
    
    context = {
        'form': form,
        'students_with_conflicts': students_with_conflicts,
        'group_summary': group_summary
    }
    
    return render(request, 'schedule/assign_trimester_courses.html', context) 