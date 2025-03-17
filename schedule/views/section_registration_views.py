import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages

from schedule.models import Student, Section, Course, CourseEnrollment, Enrollment, TrimesterCourseGroup
from schedule.forms import LanguageCourseForm, TrimesterCourseForm
from schedule.services.section_registration_services.registration_service import RegistrationService
from schedule.services.section_registration_services.language_course_service import LanguageCourseService
from schedule.services.section_registration_services.trimester_course_service import TrimesterCourseService
from schedule.services.section_registration_services.algorithm_service import AlgorithmService
from schedule.services.enrollment_services.enrollment_service import EnrollmentService

# Import placeholder functions for algorithm modules not yet refactored
from schedule.utils.algorithm_placeholders import (
    register_art_music_ww_courses,
    register_two_elective_groups,
    register_three_elective_groups
)

def registration_home(request):
    """
    Home page for the section registration system showing registration stats.
    """
    # Get all sections with their capacities and current enrollment counts
    sections = Section.objects.all().select_related('course', 'period', 'teacher', 'room')
    section_stats = RegistrationService.get_section_stats(sections)
    
    # Get course enrollment statistics
    course_enrollment_stats = RegistrationService.get_course_enrollment_stats()
    
    # Get count of students with unassigned sections
    unassigned_students_count = RegistrationService.get_unassigned_students_count()
    
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
    # Get student enrollments using EnrollmentService
    result = EnrollmentService.get_student_enrollments(student_id)
    student = result['student']
    enrollments = result['enrollments']
    
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
                
                # Call the balancing algorithm service
                result = AlgorithmService.balance_section_assignments(course_id)
                
                # Create a properly formatted response
                return JsonResponse({
                    'status': 'success' if result['success'] else 'error',
                    'message': result['message'],
                    'success_count': result['success_count'],
                    'failure_count': result['failure_count']
                })
            
            elif action == 'assign_language_core':
                grade_level = data.get('grade_level', 6)  # Default to 6th grade
                undo_depth = data.get('undo_depth', 3)    # Default undo depth
                
                # Call the language-core algorithm service
                result = AlgorithmService.register_language_and_core_courses(grade_level, undo_depth)
                
                # Create a properly formatted response
                return JsonResponse({
                    'status': 'success' if result['success'] else 'error',
                    'message': result['message'],
                    'language_success': result['language_success'],
                    'language_failure': result['language_failure'],
                    'core_success': result['core_success'],
                    'core_failure': result['core_failure']
                })
                
            elif action == 'assign_art_music_ww':
                grade_level = data.get('grade_level', 6)  # Default to 6th grade
                undo_depth = data.get('undo_depth', 3)    # Default undo depth
                
                # Call the art-music-ww algorithm
                success, message, assignments = register_art_music_ww_courses(grade_level, undo_depth)
                
                # Create a properly formatted response
                results = {
                    'status': 'error' if not success else 'success',
                    'message': message,
                    'success_count': 0,
                    'failure_count': 0
                }
                return JsonResponse(results)
                
            elif action == 'assign_two_elective_groups':
                grade_level = data.get('grade_level', 6)  # Default to 6th grade
                undo_depth = data.get('undo_depth', 3)    # Default undo depth
                
                # Call the two-group elective algorithm
                success, message, assignments = register_two_elective_groups(grade_level, undo_depth)
                
                # Create a properly formatted response
                results = {
                    'status': 'error' if not success else 'success',
                    'message': message,
                    'first_group_success': 0,
                    'first_group_failure': 0,
                    'second_group_success': 0,
                    'second_group_failure': 0
                }
                return JsonResponse(results)
                
            elif action == 'assign_three_elective_groups':
                grade_level = data.get('grade_level', 6)  # Default to 6th grade
                undo_depth = data.get('undo_depth', 3)    # Default undo depth
                
                # Call the three-group elective algorithm
                success, message, assignments = register_three_elective_groups(grade_level, undo_depth)
                
                # Create a properly formatted response
                results = {
                    'status': 'error' if not success else 'success',
                    'message': message,
                    'first_group_success': 0,
                    'first_group_failure': 0,
                    'second_group_success': 0,
                    'second_group_failure': 0,
                    'third_group_success': 0,
                    'third_group_failure': 0
                }
                return JsonResponse(results)
                
            elif action == 'deregister_all_sections':
                course_id = data.get('course_id')  # Optional: deregister for a specific course only
                grade_level = data.get('grade_level')  # Optional: deregister for a specific grade only
                
                # Use service to deregister sections
                result = RegistrationService.deregister_sections(course_id, grade_level)
                
                return JsonResponse({
                    'status': 'success',
                    'message': result['message'],
                    'deregistered_count': result['count']
                })
                
            elif action == 'clear_student_enrollments':
                student_id = data.get('student_id')
                
                if not student_id:
                    return JsonResponse({'status': 'error', 'message': 'Student ID is required'})
                
                # Clear the student's enrollments using service
                result = EnrollmentService.clear_student_enrollments(student_id)
                
                return JsonResponse({
                    'status': 'success',
                    'message': result['message'],
                    'cleared_count': result['count']
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
            
            # Perform the assignment using service
            result = LanguageCourseService.assign_language_courses(student, language_courses, preferred_period)
            
            if result['success']:
                messages.success(request, f"Successfully assigned language courses for {student.name}: {result['message']}")
                # Redirect to student schedule view
                return redirect('view_student_schedule', student_id=student_id)
            else:
                messages.error(request, f"Error assigning language courses for {student.name}: {result['message']}")
    else:
        form = LanguageCourseForm()
    
    # List students with language course conflicts
    students_with_conflicts = []
    
    # Get all students enrolled in language courses
    students = Student.objects.filter(
        course_enrollments__course__type='language'
    ).distinct()
    
    for student in students:
        conflicts = LanguageCourseService.get_language_course_conflicts(student)
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
            
            # Perform the assignment using service
            result = TrimesterCourseService.assign_trimester_courses(student, group_ids, preferred_period)
            
            if result['success']:
                messages.success(request, f"Successfully assigned trimester courses for {student.name}: {result['message']}")
                # Redirect to student schedule view
                return redirect('view_student_schedule', student_id=student_id)
            else:
                messages.error(request, f"Error assigning trimester courses for {student.name}: {result['message']}")
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
        conflicts = TrimesterCourseService.get_trimester_course_conflicts(student)
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