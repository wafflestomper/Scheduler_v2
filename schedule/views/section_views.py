from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.http import HttpResponse, JsonResponse
import csv
from ..models import Section, Course, Teacher, Room, Period, Student
from django.db import transaction


def edit_section(request, section_id):
    """Edit an existing section."""
    section = get_object_or_404(Section, pk=section_id)
    
    if request.method == 'POST':
        course_id = request.POST.get('course')
        teacher_id = request.POST.get('teacher')
        room_id = request.POST.get('room')
        period_id = request.POST.get('period')
        
        # Validate and get related objects
        course = get_object_or_404(Course, pk=course_id) if course_id else None
        teacher = get_object_or_404(Teacher, pk=teacher_id) if teacher_id else None
        room = get_object_or_404(Room, pk=room_id) if room_id else None
        period = get_object_or_404(Period, pk=period_id) if period_id else None
        
        # Update section
        try:
            with transaction.atomic():
                section.course = course
                section.teacher = teacher
                section.room = room
                section.period = period
                section.save()
                
                messages.success(request, f"Section updated successfully!")
                return redirect('master_schedule')
        except Exception as e:
            messages.error(request, f"Error updating section: {str(e)}")
    
    # For GET request or if there was an error
    courses = Course.objects.all().order_by('name')
    teachers = Teacher.objects.all().order_by('last_name', 'first_name')
    rooms = Room.objects.all().order_by('name')
    periods = Period.objects.all().order_by('start_time')
    
    context = {
        'section': section,
        'courses': courses,
        'teachers': teachers,
        'rooms': rooms,
        'periods': periods
    }
    
    return render(request, 'schedule/sections/edit_section.html', context)


def get_conflicts(request):
    """Get conflicts for visualization."""
    conflicts = find_schedule_conflicts()
    return JsonResponse(conflicts, safe=False)


def export_master_schedule(request):
    """Export the master schedule to a CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="master_schedule.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Period', 'Course', 'Teacher', 'Room', 'Students'])
    
    sections = Section.objects.all().select_related('period', 'course', 'teacher', 'room')
    
    # Group by period for better organization
    periods = Period.objects.all().order_by('start_time')
    
    for period in periods:
        period_sections = sections.filter(period=period)
        
        if not period_sections:
            writer.writerow([period.name, '', '', '', ''])
        else:
            for section in period_sections:
                # Count students in this section
                student_count = section.student_set.count()
                
                writer.writerow([
                    period.name,
                    section.course.name if section.course else '',
                    section.teacher.full_name if section.teacher else '',
                    section.room.name if section.room else '',
                    student_count
                ])
    
    # Add sections with no period assigned
    unassigned_sections = sections.filter(period__isnull=True)
    if unassigned_sections:
        for section in unassigned_sections:
            student_count = section.student_set.count()
            
            writer.writerow([
                'Unassigned',
                section.course.name if section.course else '',
                section.teacher.full_name if section.teacher else '',
                section.room.name if section.room else '',
                student_count
            ])
    
    return response


def master_schedule(request):
    """View the master schedule."""
    # Get all periods and courses
    periods = Period.objects.all().order_by('start_time')
    courses = Course.objects.all().order_by('name')
    
    # Get all sections with related objects
    sections = Section.objects.all().select_related('period', 'course', 'teacher', 'room')
    
    # Create a dictionary to organize sections by period and course
    schedule = {}
    
    for period in periods:
        schedule[period.id] = {
            'period_name': period.name,
            'sections': []
        }
        
        # Get sections for this period
        period_sections = sections.filter(period=period)
        
        for section in period_sections:
            schedule[period.id]['sections'].append({
                'id': section.id,
                'course': section.course.name if section.course else "Unassigned",
                'teacher': section.teacher.full_name if section.teacher else "Unassigned",
                'room': section.room.name if section.room else "Unassigned",
                'student_count': section.student_set.count(),
            })
    
    # Add unassigned sections
    unassigned_sections = sections.filter(period__isnull=True)
    if unassigned_sections:
        schedule['unassigned'] = {
            'period_name': "Unassigned",
            'sections': []
        }
        
        for section in unassigned_sections:
            schedule['unassigned']['sections'].append({
                'id': section.id,
                'course': section.course.name if section.course else "Unassigned",
                'teacher': section.teacher.full_name if section.teacher else "Unassigned",
                'room': section.room.name if section.room else "Unassigned",
                'student_count': section.student_set.count(),
            })
    
    context = {
        'schedule': schedule,
        'total_sections': sections.count()
    }
    
    return render(request, 'schedule/sections/master_schedule.html', context)


def student_schedules(request):
    """View student schedules."""
    student_id = request.GET.get('student_id')
    
    if student_id:
        # View a specific student's schedule
        student = get_object_or_404(Student, pk=student_id)
        sections = student.sections.all().select_related('course', 'period', 'teacher', 'room')
        
        # Group sections by period for display
        schedule = {}
        for section in sections:
            if not section.period:
                continue
            
            period_id = section.period.id
            if period_id not in schedule:
                schedule[period_id] = {
                    'period': section.period,
                    'sections': []
                }
            
            schedule[period_id]['sections'].append(section)
        
        # Sort periods by time
        sorted_schedule = {}
        for period_id in sorted(schedule.keys()):
            sorted_schedule[period_id] = schedule[period_id]
        
        return render(request, 'schedule/student_schedules.html', {
            'student': student,
            'schedule': sorted_schedule,
            'section_count': sections.count()
        })
    else:
        # List all students with their section counts
        students = Student.objects.all().order_by('name')
        
        # Get counts of sections for each student
        students_with_counts = []
        for student in students:
            section_count = student.sections.count()
            students_with_counts.append({
                'student': student,
                'section_count': section_count
            })
        
        return render(request, 'schedule/student_schedules.html', {
            'students_with_counts': students_with_counts,
            'total_students': len(students_with_counts)
        })


def find_schedule_conflicts():
    """Find schedule conflicts in the current schedule."""
    conflicts = []
    
    # Get all sections with a period assigned
    sections = Section.objects.exclude(period__isnull=True).select_related('period', 'course', 'teacher', 'room')
    
    # Check for teacher conflicts (same teacher, same period)
    teachers = Teacher.objects.all()
    for teacher in teachers:
        teacher_sections = sections.filter(teacher=teacher)
        periods_with_sections = {}
        
        for section in teacher_sections:
            period_id = section.period.id
            if period_id in periods_with_sections:
                # Conflict: Teacher assigned to multiple sections in the same period
                conflict = {
                    'type': 'teacher',
                    'description': f"Teacher {teacher.full_name} assigned to multiple sections in period {section.period.name}",
                    'sections': [
                        {
                            'id': periods_with_sections[period_id].id,
                            'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                            'period': periods_with_sections[period_id].period.name,
                            'room': periods_with_sections[period_id].room.name if periods_with_sections[period_id].room else "Unassigned"
                        },
                        {
                            'id': section.id,
                            'course': section.course.name if section.course else "Unassigned",
                            'period': section.period.name,
                            'room': section.room.name if section.room else "Unassigned"
                        }
                    ]
                }
                conflicts.append(conflict)
            else:
                periods_with_sections[period_id] = section
    
    # Check for room conflicts (same room, same period)
    rooms = Room.objects.all()
    for room in rooms:
        room_sections = sections.filter(room=room)
        periods_with_sections = {}
        
        for section in room_sections:
            period_id = section.period.id
            if period_id in periods_with_sections:
                # Conflict: Room assigned to multiple sections in the same period
                conflict = {
                    'type': 'room',
                    'description': f"Room {room.name} assigned to multiple sections in period {section.period.name}",
                    'sections': [
                        {
                            'id': periods_with_sections[period_id].id,
                            'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                            'period': periods_with_sections[period_id].period.name,
                            'teacher': periods_with_sections[period_id].teacher.full_name if periods_with_sections[period_id].teacher else "Unassigned"
                        },
                        {
                            'id': section.id,
                            'course': section.course.name if section.course else "Unassigned",
                            'period': section.period.name,
                            'teacher': section.teacher.teacher.full_name if section.teacher else "Unassigned"
                        }
                    ]
                }
                conflicts.append(conflict)
            else:
                periods_with_sections[period_id] = section
    
    # Check for student conflicts (student assigned to multiple sections in the same period)
    students = Student.objects.all()
    for student in students:
        student_sections = student.section_set.exclude(period__isnull=True)
        periods_with_sections = {}
        
        for section in student_sections:
            period_id = section.period.id
            if period_id in periods_with_sections:
                # Conflict: Student assigned to multiple sections in the same period
                conflict = {
                    'type': 'student',
                    'description': f"Student {student.full_name} assigned to multiple sections in period {section.period.name}",
                    'student_id': student.id,
                    'sections': [
                        {
                            'id': periods_with_sections[period_id].id,
                            'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                            'period': periods_with_sections[period_id].period.name,
                            'teacher': periods_with_sections[period_id].teacher.full_name if periods_with_sections[period_id].teacher else "Unassigned"
                        },
                        {
                            'id': section.id,
                            'course': section.course.name if section.course else "Unassigned",
                            'period': section.period.name,
                            'teacher': section.teacher.full_name if section.teacher else "Unassigned"
                        }
                    ]
                }
                conflicts.append(conflict)
            else:
                periods_with_sections[period_id] = section
    
    return conflicts 