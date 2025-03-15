from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
import csv
from django.views import View
from ..models import Student, Section
from ..forms import StudentForm
import json


def view_students(request):
    """View all students."""
    students = Student.objects.all().order_by('last_name', 'first_name')
    return render(request, 'schedule/students/view_students.html', {'students': students})


def student_detail(request, student_id):
    """View details for a specific student."""
    student = get_object_or_404(Student, pk=student_id)
    
    # Get all sections this student is enrolled in
    sections = student.section_set.all()
    
    # Create a schedule dictionary organized by period
    schedule = {}
    for section in sections:
        period_name = section.period.name if section.period else "Unassigned"
        if period_name not in schedule:
            schedule[period_name] = []
        schedule[period_name].append({
            'id': section.id,
            'course_name': section.course.name,
            'teacher_name': section.teacher.full_name if section.teacher else "Unassigned",
            'room_name': section.room.name if section.room else "Unassigned"
        })
    
    # Sort the periods
    sorted_schedule = {}
    for period in sorted(schedule.keys()):
        sorted_schedule[period] = schedule[period]
    
    context = {
        'student': student,
        'schedule': sorted_schedule,
        'total_sections': sections.count()
    }
    
    return render(request, 'schedule/students/student_detail.html', context)


def edit_student(request, student_id):
    """Edit an existing student."""
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Student {student.full_name} updated successfully!')
            return redirect('student_detail', student_id=student.id)
    else:
        form = StudentForm(instance=student)
    
    return render(request, 'schedule/students/edit_student.html', {'form': form, 'student': student})


def delete_student(request, student_id):
    """Delete a student."""
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        student_name = student.full_name
        student.delete()
        messages.success(request, f'Student {student_name} deleted successfully!')
        return redirect('view_students')
    
    return render(request, 'schedule/students/confirm_delete.html', {'student': student})


def export_student_schedules(request):
    """Export all student schedules to a CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_schedules.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Last Name', 'First Name', 'Grade', 'Period', 'Course', 'Teacher', 'Room'])
    
    students = Student.objects.all().order_by('last_name', 'first_name')
    
    for student in students:
        sections = student.section_set.all().select_related('period', 'course', 'teacher', 'room')
        
        if not sections:
            # Write a row for students with no sections
            writer.writerow([student.id, student.last_name, student.first_name, student.grade, '', '', '', ''])
        else:
            for section in sections:
                period_name = section.period.name if section.period else ''
                course_name = section.course.name if section.course else ''
                teacher_name = section.teacher.full_name if section.teacher else ''
                room_name = section.room.name if section.room else ''
                
                writer.writerow([
                    student.id,
                    student.last_name,
                    student.first_name,
                    student.grade,
                    period_name,
                    course_name,
                    teacher_name,
                    room_name
                ])
    
    return response 