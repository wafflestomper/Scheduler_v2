from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from ..models import Teacher, Room, Student, Course, Period, Section, Enrollment, SectionSettings, CourseEnrollment
import constraint
import json
from django.db import transaction
from ..utils.section_utils import get_sections_below_min_size, get_sections_stats


def schedule_generation(request):
    """Generate schedules page."""
    context = {
        'num_students': Student.objects.count(),
        'num_teachers': Teacher.objects.count(),
        'num_rooms': Room.objects.count(),
        'num_courses': Course.objects.count(),
        'num_sections': Section.objects.count(),
        'num_periods': Period.objects.count(),
    }
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Clear existing sections
                Section.objects.all().delete()
                
                # Generate new schedules
                generate_schedules()
                
                messages.success(request, "Schedules generated successfully!")
                
        except Exception as e:
            messages.error(request, f"Error generating schedules: {str(e)}")
    
    return render(request, 'schedule/schedule_generation.html', context)


def admin_reports(request):
    """View for admin reports."""
    # Get all data for reporting
    students = Student.objects.all()
    teachers = Teacher.objects.all()
    rooms = Room.objects.all()
    courses = Course.objects.all()
    sections = Section.objects.all().select_related('course', 'teacher', 'room', 'period')
    periods = Period.objects.all()
    
    # Calculate various statistics
    total_students = students.count()
    total_teachers = teachers.count()
    total_rooms = rooms.count()
    total_courses = courses.count()
    total_sections = sections.count()
    
    # Students by grade level
    students_by_grade = {}
    for student in students:
        grade = student.grade_level if student.grade_level is not None else 'Unknown'
        if grade not in students_by_grade:
            students_by_grade[grade] = 0
        students_by_grade[grade] += 1
    
    # Courses by type
    courses_by_type = {}
    for course in courses:
        course_type = course.type if course.type else 'Unknown'
        if course_type not in courses_by_type:
            courses_by_type[course_type] = 0
        courses_by_type[course_type] += 1
    
    # Sections by course type
    sections_by_course_type = {}
    for section in sections:
        if section.course:
            course_type = section.course.type if section.course.type else 'Unknown'
            if course_type not in sections_by_course_type:
                sections_by_course_type[course_type] = 0
            sections_by_course_type[course_type] += 1
    
    # Teacher load (number of sections per teacher)
    teacher_load = {}
    for teacher in teachers:
        teacher_sections = sections.filter(teacher=teacher)
        teacher_load[teacher.name] = teacher_sections.count()
    
    # Room utilization (number of sections per room)
    room_utilization = {}
    for room in rooms:
        room_sections = sections.filter(room=room)
        room_utilization[room.number] = room_sections.count()
    
    # Period utilization (number of sections per period)
    period_utilization = {}
    for period in periods:
        period_sections = sections.filter(period=period)
        period_utilization[str(period)] = period_sections.count()
    
    # Find any schedule conflicts
    conflicts = find_schedule_conflicts()
    
    # Get section statistics
    section_stats = get_sections_stats()
    
    # Get sections below minimum size
    sections_below_min = get_sections_below_min_size()
    
    # Prepare context for template
    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_rooms': total_rooms,
        'total_courses': total_courses,
        'total_sections': total_sections,
        'enrollment_by_grade': students_by_grade,
        'courses_by_type': courses_by_type,
        'sections_by_course_type': sections_by_course_type,
        'teacher_load': teacher_load,
        'room_utilization': room_utilization,
        'period_utilization': period_utilization,
        'conflicts': conflicts,
        'conflict_count': len(conflicts),
        'section_stats': section_stats,
        'sections_below_min': sections_below_min,
        'settings': SectionSettings.objects.first(),
    }
    
    return render(request, 'schedule/admin_reports.html', context)


def generate_schedules():
    """Generate course schedules."""
    # Get all data
    courses = Course.objects.all()
    teachers = Teacher.objects.all()
    rooms = Room.objects.all()
    periods = Period.objects.all()
    students = Student.objects.all()
    
    # Create sections for core courses first
    create_core_sections(courses, teachers, rooms, periods)
    
    # Assign students to core sections
    assign_students_to_core_sections(students)
    
    # Create sections for elective courses
    create_elective_sections(courses, teachers, rooms, periods)
    
    # Assign students to elective sections
    assign_students_to_elective_sections(students)


def create_core_sections(courses, teachers, rooms, periods):
    """Create sections for core courses."""
    # Get core courses (Math, Science, English, Social Studies)
    core_courses = courses.filter(type__in=['core'])
    
    # For each core course, create the required number of sections
    for course in core_courses:
        for i in range(course.sections_needed):
            # Find an available teacher, room, and period
            available_teachers = list(teachers)
            available_rooms = list(rooms)
            available_periods = list(periods)
            
            # Shuffle to randomize assignments
            import random
            random.shuffle(available_teachers)
            random.shuffle(available_rooms)
            random.shuffle(available_periods)
            
            # Attempt to find a valid assignment
            assigned = False
            for teacher in available_teachers:
                if assigned:
                    break
                
                for room in available_rooms:
                    if assigned:
                        break
                    
                    for period in available_periods:
                        # Check if this teacher is already teaching during this period
                        if Section.objects.filter(teacher=teacher, period=period).exists():
                            continue
                        
                        # Check if this room is already in use during this period
                        if Section.objects.filter(room=room, period=period).exists():
                            continue
                        
                        # Create the section
                        section_id = f"{course.id}-{i+1}"
                        section = Section(
                            id=section_id,
                            course=course,
                            section_number=i+1,
                            teacher=teacher,
                            room=room,
                            period=period
                        )
                        section.save()
                        assigned = True
                        break
            
            # If we couldn't find a valid assignment, create an unassigned section
            if not assigned:
                section_id = f"{course.id}-{i+1}"
                section = Section(
                    id=section_id,
                    course=course,
                    section_number=i+1
                )
                section.save()


def assign_students_to_core_sections(students):
    """Assign students to core course sections."""
    # Get core courses
    core_courses = Course.objects.filter(type='core')
    
    # For each student, assign to appropriate core courses
    for student in students:
        for course in core_courses:
            # Skip if course is not for this student's grade level
            if course.grade_level != student.grade_level:
                continue
            
            # Find sections for this course
            course_sections = Section.objects.filter(course=course)
            
            if not course_sections:
                continue
            
            # Find section with fewest students
            best_section = None
            min_students = float('inf')
            
            for section in course_sections:
                section_student_count = section.students.count()
                if section_student_count < min_students and section_student_count < course.max_students:
                    min_students = section_student_count
                    best_section = section
            
            # Assign student to best section if found
            if best_section:
                from ..models import Enrollment
                Enrollment.objects.get_or_create(student=student, section=best_section)


def create_elective_sections(courses, teachers, rooms, periods):
    """Create sections for elective courses."""
    # Get elective courses
    elective_courses = courses.filter(type__in=['elective', 'required_elective', 'language'])
    
    # For each elective course, create the required number of sections
    for course in elective_courses:
        for i in range(course.sections_needed):
            # Find an available teacher, room, and period
            available_teachers = list(teachers)
            available_rooms = list(rooms)
            available_periods = list(periods)
            
            # Shuffle to randomize assignments
            import random
            random.shuffle(available_teachers)
            random.shuffle(available_rooms)
            random.shuffle(available_periods)
            
            # Attempt to find a valid assignment
            assigned = False
            for teacher in available_teachers:
                if assigned:
                    break
                
                for room in available_rooms:
                    if assigned:
                        break
                    
                    for period in available_periods:
                        # Check if this teacher is already teaching during this period
                        if Section.objects.filter(teacher=teacher, period=period).exists():
                            continue
                        
                        # Check if this room is already in use during this period
                        if Section.objects.filter(room=room, period=period).exists():
                            continue
                        
                        # Create the section
                        section_id = f"{course.id}-{i+1}"
                        section = Section(
                            id=section_id,
                            course=course,
                            section_number=i+1,
                            teacher=teacher,
                            room=room,
                            period=period
                        )
                        section.save()
                        assigned = True
                        break
            
            # If we couldn't find a valid assignment, create an unassigned section
            if not assigned:
                section_id = f"{course.id}-{i+1}"
                section = Section(
                    id=section_id,
                    course=course,
                    section_number=i+1
                )
                section.save()


def assign_students_to_elective_sections(students):
    """Assign students to elective course sections."""
    # Get elective courses
    elective_courses = Course.objects.filter(type__in=['elective', 'required_elective', 'language'])
    
    # For each student, assign to appropriate elective courses
    for student in students:
        # Get periods already assigned to this student
        assigned_periods = set()
        for section in student.sections.all():
            if section.period:
                assigned_periods.add(section.period.id)
        
        # Try to assign 2 electives per student if possible
        electives_assigned = 0
        
        for course in elective_courses:
            if electives_assigned >= 2:
                break
                
            # Skip if course is not for this student's grade level
            if course.grade_level != student.grade_level:
                continue
            
            # Find sections for this course
            course_sections = Section.objects.filter(course=course)
            
            if not course_sections:
                continue
            
            # Find section with fewest students that doesn't conflict with student's schedule
            best_section = None
            min_students = float('inf')
            
            for section in course_sections:
                # Skip if section has no period assigned
                if not section.period:
                    continue
                    
                # Skip if period conflicts with student's existing schedule
                if section.period.id in assigned_periods:
                    continue
                
                section_student_count = section.students.count()
                if section_student_count < min_students and section_student_count < course.max_students:
                    min_students = section_student_count
                    best_section = section
            
            # Assign student to best section if found
            if best_section:
                from ..models import Enrollment
                Enrollment.objects.get_or_create(student=student, section=best_section)
                if best_section.period:
                    assigned_periods.add(best_section.period.id)
                electives_assigned += 1


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
                    'description': f"Teacher {teacher.name} assigned to multiple sections in period {section.period.id}",
                    'sections': [
                        {
                            'id': periods_with_sections[period_id].id,
                            'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                            'period': periods_with_sections[period_id].period.id,
                            'room': periods_with_sections[period_id].room.number if periods_with_sections[period_id].room else "Unassigned"
                        },
                        {
                            'id': section.id,
                            'course': section.course.name if section.course else "Unassigned",
                            'period': section.period.id,
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
                    'description': f"Room {room.number} assigned to multiple sections in period {section.period.id}",
                    'sections': [
                        {
                            'id': periods_with_sections[period_id].id,
                            'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                            'period': periods_with_sections[period_id].period.id,
                            'teacher': periods_with_sections[period_id].teacher.name if periods_with_sections[period_id].teacher else "Unassigned"
                        },
                        {
                            'id': section.id,
                            'course': section.course.name if section.course else "Unassigned",
                            'period': section.period.id,
                            'teacher': section.teacher.name if section.teacher else "Unassigned"
                        }
                    ]
                }
                conflicts.append(conflict)
            else:
                periods_with_sections[period_id] = section
    
    # Check for student conflicts (student assigned to multiple sections in the same period)
    students = Student.objects.all()
    for student in students:
        student_sections = student.sections.exclude(period__isnull=True)
        periods_with_sections = {}
        
        for section in student_sections:
            period_id = section.period.id
            if period_id in periods_with_sections:
                # Conflict: Student assigned to multiple sections in the same period
                conflict = {
                    'type': 'student',
                    'description': f"Student {student.name} assigned to multiple sections in period {section.period.id}",
                    'student_id': student.id,
                    'sections': [
                        {
                            'id': periods_with_sections[period_id].id,
                            'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                            'period': periods_with_sections[period_id].period.id,
                            'teacher': periods_with_sections[period_id].teacher.name if periods_with_sections[period_id].teacher else "Unassigned"
                        },
                        {
                            'id': section.id,
                            'course': section.course.name if section.course else "Unassigned",
                            'period': section.period.id,
                            'teacher': section.teacher.name if section.teacher else "Unassigned"
                        }
                    ]
                }
                conflicts.append(conflict)
            else:
                periods_with_sections[period_id] = section
    
    return conflicts 