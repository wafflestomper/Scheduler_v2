from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.http import HttpResponse, JsonResponse
import csv
from ..models import Section, Course, Teacher, Room, Period, Student, Enrollment
from django.db import transaction
from django.db.models import Count, Q


def edit_section(request, section_id):
    """Edit an existing section."""
    section = get_object_or_404(Section, pk=section_id)
    
    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id')
        room_id = request.POST.get('room_id')
        period_id = request.POST.get('period_id')
        max_size = request.POST.get('max_size')
        
        # Validate and get related objects
        teacher = get_object_or_404(Teacher, pk=teacher_id) if teacher_id else None
        room = get_object_or_404(Room, pk=room_id) if room_id else None
        period = get_object_or_404(Period, pk=period_id) if period_id else None
        
        # Validate max_size
        if max_size:
            try:
                max_size = int(max_size)
                if max_size <= 0:
                    messages.error(request, "Max size must be a positive integer")
                    return redirect('edit_section', section_id=section_id)
            except ValueError:
                messages.error(request, "Max size must be a valid number")
                return redirect('edit_section', section_id=section_id)
        else:
            max_size = None
        
        # Update section
        try:
            with transaction.atomic():
                section.teacher = teacher
                section.room = room
                section.period = period
                section.max_size = max_size
                section.save()
                
                messages.success(request, f"Section updated successfully!")
                return redirect('master_schedule')
        except Exception as e:
            messages.error(request, f"Error updating section: {str(e)}")
    
    # For GET request or if there was an error
    courses = Course.objects.all().order_by('name')
    teachers = Teacher.objects.all().order_by('name')
    rooms = Room.objects.all().order_by('number')
    periods = Period.objects.all().order_by('start_time')
    
    context = {
        'section': section,
        'courses': courses,
        'teachers': teachers,
        'rooms': rooms,
        'periods': periods
    }
    
    return render(request, 'schedule/edit_section.html', context)


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
            writer.writerow([period.period_name, '', '', '', ''])
        else:
            for section in period_sections:
                # Count students in this section
                student_count = section.students.count()
                
                writer.writerow([
                    period.period_name,
                    section.course.name if section.course else '',
                    section.teacher.full_name if section.teacher else '',
                    section.room.number if section.room else '',
                    student_count
                ])
    
    # Add sections with no period assigned
    unassigned_sections = sections.filter(period__isnull=True)
    if unassigned_sections:
        for section in unassigned_sections:
            student_count = section.students.count()
            
            writer.writerow([
                'Unassigned',
                section.course.name if section.course else '',
                section.teacher.full_name if section.teacher else '',
                section.room.number if section.room else '',
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
            'period_name': period.period_name,
            'sections': []
        }
        
        # Get sections for this period
        period_sections = sections.filter(period=period)
        
        for section in period_sections:
            schedule[period.id]['sections'].append({
                'id': section.id,
                'course': section.course.name if section.course else "Unassigned",
                'teacher': section.teacher.full_name if section.teacher else "Unassigned",
                'room': section.room.number if section.room else "Unassigned",
                'student_count': section.students.count(),
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
                'room': section.room.number if section.room else "Unassigned",
                'student_count': section.students.count(),
            })
    
    context = {
        'schedule': schedule,
        'total_sections': sections.count()
    }
    
    return render(request, 'schedule/master_schedule.html', context)


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
                    'description': f"Teacher {teacher.full_name} assigned to multiple sections in period {section.period.period_name}",
                    'sections': [
                        {
                            'id': periods_with_sections[period_id].id,
                            'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                            'period': periods_with_sections[period_id].period.period_name,
                            'room': periods_with_sections[period_id].room.number if periods_with_sections[period_id].room else "Unassigned"
                        },
                        {
                            'id': section.id,
                            'course': section.course.name if section.course else "Unassigned",
                            'period': section.period.period_name,
                            'room': section.room.number if section.room else "Unassigned"
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
                    'description': f"Room {room.number} assigned to multiple sections in period {section.period.period_name}",
                    'sections': [
                        {
                            'id': periods_with_sections[period_id].id,
                            'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                            'period': periods_with_sections[period_id].period.period_name,
                            'teacher': periods_with_sections[period_id].teacher.full_name if periods_with_sections[period_id].teacher else "Unassigned"
                        },
                        {
                            'id': section.id,
                            'course': section.course.name if section.course else "Unassigned",
                            'period': section.period.period_name,
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
                    'description': f"Student {student.full_name} assigned to multiple sections in period {section.period.period_name}",
                    'student_id': student.id,
                    'sections': [
                        {
                            'id': periods_with_sections[period_id].id,
                            'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                            'period': periods_with_sections[period_id].period.period_name,
                            'teacher': periods_with_sections[period_id].teacher.full_name if periods_with_sections[period_id].teacher else "Unassigned"
                        },
                        {
                            'id': section.id,
                            'course': section.course.name if section.course else "Unassigned",
                            'period': section.period.period_name,
                            'teacher': section.teacher.full_name if section.teacher else "Unassigned"
                        }
                    ]
                }
                conflicts.append(conflict)
            else:
                periods_with_sections[period_id] = section
    
    return conflicts


def section_roster(request, course_id):
    """View to display the roster of students enrolled in each section of a course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Get all sections for this course
    sections = Section.objects.filter(course=course).select_related('teacher', 'period', 'room')
    
    # Initialize data structure to hold section rosters
    section_rosters = []
    
    for section in sections:
        # Get students enrolled in this section
        enrollments = Enrollment.objects.filter(section=section).select_related('student')
        students = [enrollment.student for enrollment in enrollments]
        
        # Sort students by name for consistent display
        students.sort(key=lambda x: x.name)
        
        section_rosters.append({
            'section': section,
            'students': students,
            'enrollment_count': len(students),
            'max_size': section.max_size or 'Unlimited'
        })
    
    # Sort sections by section number
    section_rosters.sort(key=lambda x: x['section'].section_number)
    
    context = {
        'course': course,
        'section_rosters': section_rosters,
        'total_sections': len(section_rosters),
        'total_students': sum(len(roster['students']) for roster in section_rosters)
    }
    
    return render(request, 'schedule/section_roster.html', context)


def check_conflicts(request, section_id):
    """Check conflicts for a specific section."""
    section = get_object_or_404(Section, pk=section_id)
    conflicts = []

    # Check for teacher conflicts
    if section.teacher and section.period:
        teacher_conflicts = Section.objects.filter(
            teacher=section.teacher,
            period=section.period
        ).exclude(id=section.id)
        
        if teacher_conflicts.exists():
            for conflict in teacher_conflicts:
                conflicts.append({
                    'type': 'teacher',
                    'message': f"Teacher {section.teacher.name} is already assigned to {conflict.course.name} section {conflict.section_number} during this period"
                })
    
    # Check for room conflicts
    if section.room and section.period:
        room_conflicts = Section.objects.filter(
            room=section.room,
            period=section.period
        ).exclude(id=section.id)
        
        if room_conflicts.exists():
            for conflict in room_conflicts:
                conflicts.append({
                    'type': 'room',
                    'message': f"Room {section.room.number} is already assigned to {conflict.course.name} section {conflict.section_number} during this period"
                })
    
    # Check for student conflicts
    student_conflicts = []
    if section.period:
        for student in section.students.all():
            other_sections = student.sections.filter(period=section.period).exclude(id=section.id)
            if other_sections.exists():
                student_conflicts.append({
                    'student': student.name,
                    'conflicts': [f"{s.course.name} section {s.section_number}" for s in other_sections]
                })
    
    if student_conflicts:
        conflicts.append({
            'type': 'student',
            'message': "Some students have conflicts with this section",
            'details': student_conflicts
        })
    
    return JsonResponse({
        'section_id': section.id,
        'section_name': f"{section.course.name} section {section.section_number}",
        'conflicts': conflicts,
        'has_conflicts': len(conflicts) > 0
    })


def view_sections(request):
    """View all sections."""
    # Get all sections with related objects
    sections = Section.objects.all().select_related('course', 'teacher', 'period', 'room')
    
    # Group sections by course for better organization
    sections_by_course = {}
    
    for section in sections:
        course_id = section.course.id if section.course else 'unassigned'
        course_name = section.course.name if section.course else 'Unassigned'
        
        if course_id not in sections_by_course:
            sections_by_course[course_id] = {
                'course_name': course_name,
                'sections': []
            }
        
        # Add section details
        sections_by_course[course_id]['sections'].append({
            'id': section.id,
            'section_number': section.section_number,
            'teacher': section.teacher.name if section.teacher else 'Unassigned',
            'period': section.period.period_name if section.period else 'Unassigned',
            'room': section.room.number if section.room else 'Unassigned',
            'students_count': section.students.count(),
            'max_size': section.max_size or 'Unlimited',
            'when': section.when
        })
    
    context = {
        'sections_by_course': sections_by_course,
        'total_sections': sections.count()
    }
    
    return render(request, 'schedule/view_sections.html', context)


def add_section(request):
    """Add a new section."""
    if request.method == 'POST':
        course_id = request.POST.get('course')
        teacher_id = request.POST.get('teacher')
        period_id = request.POST.get('period')
        room_id = request.POST.get('room')
        section_number = request.POST.get('section_number')
        max_size = request.POST.get('max_size')
        when = request.POST.get('when')
        
        # Validate input
        if not course_id:
            messages.error(request, "Course is required")
            return redirect('add_section')
        
        try:
            section_number = int(section_number)
        except (ValueError, TypeError):
            messages.error(request, "Section number must be a valid integer")
            return redirect('add_section')
        
        if max_size:
            try:
                max_size = int(max_size)
                if max_size <= 0:
                    raise ValueError()
            except ValueError:
                messages.error(request, "Max size must be a positive integer")
                return redirect('add_section')
        
        # Get related objects
        course = get_object_or_404(Course, id=course_id)
        teacher = Teacher.objects.filter(id=teacher_id).first()
        period = Period.objects.filter(id=period_id).first()
        room = Room.objects.filter(id=room_id).first()
        
        # Generate a unique section ID
        section_id = f"{course_id}_S{section_number}"
        
        # Check if this section ID already exists
        if Section.objects.filter(id=section_id).exists():
            messages.error(request, f"Section ID {section_id} already exists. Please use a different section number.")
            return redirect('add_section')
        
        # Create the section
        section = Section(
            id=section_id,
            course=course,
            section_number=section_number,
            teacher=teacher,
            period=period,
            room=room,
            max_size=max_size,
            when=when
        )
        
        try:
            section.save()
            messages.success(request, f"Section {section_id} created successfully!")
            return redirect('view_sections')
        except Exception as e:
            messages.error(request, f"Error creating section: {str(e)}")
            return redirect('add_section')
    
    # For GET request, show the form
    courses = Course.objects.all().order_by('name')
    teachers = Teacher.objects.all().order_by('name')
    periods = Period.objects.all().order_by('slot')
    rooms = Room.objects.all().order_by('number')
    
    context = {
        'courses': courses,
        'teachers': teachers,
        'periods': periods,
        'rooms': rooms,
        'when_choices': Section._meta.get_field('when').choices
    }
    
    return render(request, 'schedule/add_section.html', context)


def delete_section(request, section_id):
    """Delete a section."""
    section = get_object_or_404(Section, id=section_id)
    
    if request.method == 'POST':
        # Check if there are any students enrolled in this section
        if section.students.exists():
            messages.error(request, f"Cannot delete section {section.id} because it has students enrolled.")
            return redirect('view_sections')
        
        # Delete the section
        section.delete()
        messages.success(request, f"Section {section.id} deleted successfully!")
        return redirect('view_sections')
    
    return render(request, 'schedule/delete_section_confirm.html', {'section': section}) 