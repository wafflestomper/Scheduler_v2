from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
import csv
from django.views import View
from ..models import Student, Section, Enrollment, Course, Period
from ..forms import StudentForm
import json
from django.db.models import Q, Count


def view_students(request):
    """View all students."""
    # Get query parameters
    search_query = request.GET.get('search', '')
    grade_filter = request.GET.get('grade', '')
    
    # Start with all students
    students = Student.objects.all()
    
    # Apply search filter if provided
    if search_query:
        students = students.filter(name__icontains=search_query)
    
    # Apply grade filter if provided
    if grade_filter:
        students = students.filter(grade_level=grade_filter)
    
    # Order by grade_level and name
    students = students.order_by('grade_level', 'name')
    
    # Get list of students who have schedules
    scheduled_students = set(Enrollment.objects.values_list('student_id', flat=True).distinct())
    
    # Group students by grade
    students_by_grade = {}
    for student in students:
        grade = student.grade_level
        if grade not in students_by_grade:
            students_by_grade[grade] = []
        students_by_grade[grade].append(student)
    
    # Sort grades
    sorted_grades = sorted(students_by_grade.keys())
    
    context = {
        'students_by_grade': students_by_grade,
        'sorted_grades': sorted_grades,
        'total_students': students.count(),
        'search_query': search_query,
        'grade_filter': grade_filter,
        'scheduled_students': scheduled_students,
    }
    
    return render(request, 'schedule/view_students.html', context)


def student_detail(request, student_id):
    """View details for a specific student."""
    student = get_object_or_404(Student, pk=student_id)
    
    # Get all periods for organizing the schedule
    periods = Period.objects.all().order_by('slot')
    
    # Get all sections this student is enrolled in
    sections = student.sections.all().select_related('course', 'teacher', 'room', 'period')
    
    # Create a dictionary of periods with their assigned sections
    period_dict = {}
    for period in periods:
        period_dict[period.id] = {
            'period': period,
            'section': None
        }
    
    # Assign sections to their periods
    for section in sections:
        if section.period and section.period.id in period_dict:
            period_dict[section.period.id]['section'] = section
    
    context = {
        'student': student,
        'period_dict': period_dict,
        'has_schedule': sections.exists(),
        'total_sections': sections.count()
    }
    
    return render(request, 'schedule/student_detail.html', context)


def edit_student(request, student_id):
    """Edit an existing student."""
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Student {student.name} updated successfully!')
            return redirect('student_detail', student_id=student.id)
    else:
        form = StudentForm(instance=student)
    
    return render(request, 'schedule/edit_student.html', {'form': form, 'student': student})


def delete_student(request, student_id):
    """Delete a student."""
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        student_name = student.name
        student.delete()
        messages.success(request, f'Student {student_name} deleted successfully!')
        return redirect('view_students')
    
    return render(request, 'schedule/delete_student_confirm.html', {'student': student})


def export_student_schedules(request):
    """Export all student schedules to a CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_schedules.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Name', 'Grade', 'Period', 'Course', 'Teacher', 'Room'])
    
    students = Student.objects.all().order_by('name')
    
    for student in students:
        sections = student.sections.all().select_related('period', 'course', 'teacher', 'room')
        
        if not sections:
            # Write a row for students with no sections
            writer.writerow([student.id, student.name, student.grade_level, '', '', '', ''])
        else:
            for section in sections:
                period_id = section.period.id if section.period else ''
                course_name = section.course.name if section.course else ''
                teacher_name = section.teacher.name if section.teacher else ''
                room_number = section.room.number if section.room else ''
                
                writer.writerow([
                    student.id,
                    student.name,
                    student.grade_level,
                    period_id,
                    course_name,
                    teacher_name,
                    room_number
                ])
    
    return response


def student_schedule(request, student_id):
    """
    View a student's class schedule in a user-friendly format.
    Shows all classes the student is registered for, organized by period.
    """
    student = get_object_or_404(Student, pk=student_id)
    
    # Get all periods for organizing the schedule
    periods = Period.objects.all().order_by('start_time')
    
    # Get all section enrollments for this student
    enrollments = Enrollment.objects.filter(
        student=student
    ).select_related(
        'section', 
        'section__course', 
        'section__period', 
        'section__teacher', 
        'section__room'
    )
    
    # Get courses the student is enrolled in but not assigned to sections
    enrolled_course_ids = [enrollment.section.course.id for enrollment in enrollments]
    unassigned_courses = Course.objects.filter(
        student_enrollments__student=student
    ).exclude(
        id__in=enrolled_course_ids
    )
    
    # Group enrollments by period for display
    schedule_by_period = {}
    unscheduled_sections = []
    
    for enrollment in enrollments:
        section = enrollment.section
        if section.period:
            period_id = section.period.id
            if period_id not in schedule_by_period:
                schedule_by_period[period_id] = {
                    'period': section.period,
                    'sections': []
                }
            schedule_by_period[period_id]['sections'].append(section)
        else:
            unscheduled_sections.append(section)
    
    # Sort the periods by their start time
    sorted_schedule = {}
    for period in periods:
        if period.id in schedule_by_period:
            sorted_schedule[period.id] = schedule_by_period[period.id]
    
    context = {
        'student': student,
        'schedule': sorted_schedule,
        'unscheduled_sections': unscheduled_sections,
        'unassigned_courses': unassigned_courses,
        'total_sections': enrollments.count()
    }
    
    return render(request, 'schedule/student_schedule_view.html', context) 