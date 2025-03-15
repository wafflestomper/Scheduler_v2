from django.shortcuts import render, redirect, get_object_or_404
import csv
from io import StringIO
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views import View
from .models import Teacher, Room, Student, Course, Period, Section
from .forms import CSVUploadForm, StudentForm
from django.db import transaction
from django.core.exceptions import ValidationError
import constraint
import json

def index(request):
    context = {
        'num_students': Student.objects.count(),
        'num_teachers': Teacher.objects.count(),
        'num_rooms': Room.objects.count(),
        'num_courses': Course.objects.count(),
        'num_sections': Section.objects.count(),
    }
    return render(request, 'schedule/index.html', context)

class CSVUploadView(View):
    template_name = 'schedule/csv_upload.html'
    
    def get(self, request):
        form = CSVUploadForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            data_type = form.cleaned_data['data_type']
            
            # Check if file is CSV
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'File is not a CSV')
                return render(request, self.template_name, {'form': form})
            
            # Read the file
            try:
                decoded_file = csv_file.read().decode('utf-8')
                io_string = StringIO(decoded_file)
                reader = csv.DictReader(io_string)
                
                # Process based on data type
                with transaction.atomic():
                    if data_type == 'students':
                        self.process_students(reader)
                    elif data_type == 'teachers':
                        self.process_teachers(reader)
                    elif data_type == 'rooms':
                        self.process_rooms(reader)
                    elif data_type == 'courses':
                        self.process_courses(reader)
                    elif data_type == 'periods':
                        self.process_periods(reader)
                    elif data_type == 'sections':
                        self.process_sections(reader)
                
                messages.success(request, f'Successfully processed {data_type} data')
                return redirect('csv_upload')
            
            except Exception as e:
                messages.error(request, f'Error processing CSV: {str(e)}')
                return render(request, self.template_name, {'form': form})
        
        return render(request, self.template_name, {'form': form})
    
    def process_students(self, reader):
        for row in reader:
            full_name = f"{row['first_name']}"
            if row.get('nickname'):
                full_name += f" '{row['nickname']}'"
            full_name += f" {row['last_name']}"
            
            Student.objects.update_or_create(
                id=row['student_id'],
                defaults={
                    'name': full_name,
                    'grade_level': int(row['grade_level']),
                    'preferences': '',  # No longer using elective_prefs
                }
            )
    
    def process_teachers(self, reader):
        for row in reader:
            Teacher.objects.update_or_create(
                id=row['teacher_id'],
                defaults={
                    'name': f"{row['first_name']} {row.get('last_name', '')}",
                    'availability': row.get('availability', ''),
                    'subjects': row.get('subjects', ''),
                }
            )
    
    def process_rooms(self, reader):
        for row in reader:
            Room.objects.update_or_create(
                id=row['room_id'],
                defaults={
                    'number': row['number'],
                    'capacity': int(row['capacity']),
                    'type': row['type'],
                }
            )
    
    def process_courses(self, reader):
        for row in reader:
            # Normalize course type - convert to lowercase and replace spaces with underscores
            course_type = row.get('course_type', 'core').lower().strip()
            # Map various forms to our standard values
            if 'core' in course_type:
                course_type = 'core'
            elif 'required' in course_type and 'elective' in course_type:
                course_type = 'required_elective'
            elif 'elective' in course_type:
                course_type = 'elective'
            elif 'language' in course_type:
                course_type = 'language'
            else:
                course_type = 'core'  # Default if not matched
            
            # Normalize duration - convert to lowercase and strip whitespace
            duration = row.get('duration', 'year').lower().strip()
            # Map various forms to our standard values
            if 'year' in duration:
                duration = 'year'
            elif 'trimester' in duration:
                duration = 'trimester'
            elif 'quarter' in duration:
                duration = 'quarter'
            else:
                duration = 'year'  # Default if not matched
            
            # Parse sections_needed, default to 1 if not provided or invalid
            try:
                sections_needed = int(row.get('sections_needed', 1))
            except ValueError:
                sections_needed = 1
            
            # Parse max_students, default to 30 if not provided or invalid
            try:
                max_students = int(row.get('max_size', 30))
            except ValueError:
                max_students = 30
                
            Course.objects.update_or_create(
                id=row['course_id'],
                defaults={
                    'name': row['name'],
                    'type': course_type,
                    'grade_level': int(row['grade_level']),
                    'max_students': max_students,
                    'eligible_teachers': row.get('teachers', ''),
                    'duration': duration,
                    'sections_needed': sections_needed,
                }
            )
    
    def process_periods(self, reader):
        for row in reader:
            # Parse time strings to Django TimeField format
            start_time = row['start_time']
            end_time = row['end_time']
            
            Period.objects.update_or_create(
                id=row['period_id'],
                defaults={
                    'day': 'M',  # Default to Monday since day is no longer in CSV
                    'slot': 1,   # Default to slot 1 since slot is no longer in CSV
                    'start_time': start_time,
                    'end_time': end_time,
                }
            )
            
    def process_sections(self, reader):
        for row in reader:
            # Get the related objects
            try:
                course = Course.objects.get(id=row['course_id'])
                teacher = Teacher.objects.get(id=row['teacher'])
                period = Period.objects.get(id=row['period'])
                room = Room.objects.get(id=row['room'])
                
                # Create or update the section
                # Note: we're generating a unique ID based on course and section number
                section_id = f"{row['course_id']}_S{row['section_number']}"
                
                Section.objects.update_or_create(
                    id=section_id,
                    defaults={
                        'course': course,
                        'teacher': teacher,
                        'room': room,
                        'period': period,
                        'students': '',  # Empty initially, students will be assigned later
                    }
                )
            except (Course.DoesNotExist, Teacher.DoesNotExist, Period.DoesNotExist, Room.DoesNotExist) as e:
                # Raise a more descriptive error
                entity_type = str(e).split('.')[0]
                raise ValidationError(f"Invalid {entity_type} reference in section data: {str(e)}")

def schedule_generation(request):
    if request.method == 'POST':
        # Clear existing sections
        Section.objects.all().delete()
        
        try:
            # Call the scheduling algorithm function
            generate_schedules()
            messages.success(request, 'Schedules generated successfully!')
        except Exception as e:
            messages.error(request, f'Error generating schedules: {str(e)}')
        
        return redirect('master_schedule')
    
    return render(request, 'schedule/schedule_generation.html')

def master_schedule(request):
    sections = Section.objects.all().select_related('course', 'teacher', 'room', 'period')
    periods = Period.objects.all().order_by('day', 'slot')
    
    # Group sections by day and period for easier display
    schedule_by_period = {}
    for period in periods:
        schedule_by_period[period.id] = {
            'period': period,
            'sections': sections.filter(period=period)
        }
    
    context = {
        'schedule_by_period': schedule_by_period,
        'periods': periods,
    }
    
    return render(request, 'schedule/master_schedule.html', context)

def student_schedules(request):
    students = Student.objects.all().order_by('grade_level', 'name')
    
    # Get all sections
    sections = Section.objects.all().select_related('course', 'teacher', 'room', 'period')
    
    # Build schedules for each student
    student_schedules = {}
    for student in students:
        student_schedules[student.id] = {
            'student': student,
            'schedule': []
        }
        
        # Find sections this student is in
        for section in sections:
            if student.id in section.get_students_list():
                student_schedules[student.id]['schedule'].append(section)
    
    context = {
        'student_schedules': student_schedules,
    }
    
    return render(request, 'schedule/student_schedules.html', context)

def edit_section(request, section_id):
    try:
        section = Section.objects.get(id=section_id)
        
        if request.method == 'POST':
            # Get form data
            teacher_id = request.POST.get('teacher_id')
            room_id = request.POST.get('room_id')
            period_id = request.POST.get('period_id')
            
            # Update section
            if teacher_id:
                section.teacher_id = teacher_id
            if room_id:
                section.room_id = room_id
            if period_id:
                section.period_id = period_id
            
            # Save changes
            section.save()
            messages.success(request, 'Section updated successfully!')
            return redirect('master_schedule')
        
        # Get available teachers, rooms, periods for dropdown
        teachers = Teacher.objects.all()
        rooms = Room.objects.all()
        periods = Period.objects.all()
        
        context = {
            'section': section,
            'teachers': teachers,
            'rooms': rooms, 
            'periods': periods,
        }
        
        return render(request, 'schedule/edit_section.html', context)
    
    except Section.DoesNotExist:
        messages.error(request, 'Section not found.')
        return redirect('master_schedule')

def get_conflicts(request):
    conflicts = find_schedule_conflicts()
    return JsonResponse({'conflicts': conflicts})

def export_student_schedules(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_schedules.csv"'
    
    writer = csv.writer(response)
    
    # Get all periods for headers
    periods = Period.objects.all().order_by('day', 'slot')
    
    # Write header row
    header = ['Student ID', 'Student Name', 'Grade']
    for period in periods:
        header.append(f"{period.get_day_display()} Period {period.slot}")
    writer.writerow(header)
    
    # Get all students
    students = Student.objects.all().order_by('grade_level', 'name')
    
    # Get all sections
    sections = Section.objects.all().select_related('course', 'teacher', 'room', 'period')
    
    # Write student schedules
    for student in students:
        row = [student.id, student.name, student.grade_level]
        
        # For each period, find if the student has a class
        for period in periods:
            class_name = ''
            for section in sections:
                if student.id in section.get_students_list() and section.period == period:
                    class_name = f"{section.course.name} ({section.room.number})"
                    break
            row.append(class_name)
        
        writer.writerow(row)
    
    return response

def export_master_schedule(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="master_schedule.csv"'
    
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow(['Period', 'Course', 'Teacher', 'Room', 'Students'])
    
    # Get all sections
    sections = Section.objects.all().select_related('course', 'teacher', 'room', 'period')
    
    # Write sections
    for section in sections:
        writer.writerow([
            str(section.period),
            section.course.name,
            section.teacher.name,
            section.room.number,
            len(section.get_students_list())
        ])
    
    return response

def download_template_csv(request, template_type):
    """Serve empty CSV templates with headers for each data type."""
    if template_type not in ['students', 'teachers', 'rooms', 'courses', 'periods', 'sections']:
        return HttpResponse("Invalid template type", status=400)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{template_type}_template.csv"'
    
    writer = csv.writer(response)
    
    # Write appropriate headers based on template type
    if template_type == 'students':
        writer.writerow(['student_id', 'first_name', 'nickname', 'last_name', 'grade_level'])
        # Add a sample row
        writer.writerow(['S001', 'John', 'Johnny', 'Doe', '6'])
        writer.writerow(['S002', 'Jane', '', 'Smith', '7'])
    elif template_type == 'teachers':
        writer.writerow(['teacher_id', 'first_name', 'last_name', 'availability', 'grade_level', 'subjects', 'gender'])
        # Add a sample row
        writer.writerow(['T001', 'Sarah', 'Smith', 'M1-M6,T1-T3', '6,7,8', 'Math|Science', 'F'])
        writer.writerow(['T002', 'Robert', 'Johnson', 'M1-M6,T1-T6,W1-W6', '7,8', 'English|History', 'M'])
    elif template_type == 'rooms':
        writer.writerow(['room_id', 'number', 'capacity', 'type'])
        # Add a sample row
        writer.writerow(['R001', '101', '30', 'classroom'])
    elif template_type == 'courses':
        writer.writerow(['course_id', 'name', 'course_type', 'teachers', 'grade_level', 'sections_needed', 'duration', 'max_size'])
        # Add sample rows
        writer.writerow(['C001', 'Math 6', 'core', 'T001|T002', '6', '2', 'year', '30'])
        writer.writerow(['C002', 'Art', 'elective', 'T003', '0', '1', 'trimester', '25'])
        writer.writerow(['C003', 'Spanish I', 'language', 'T004', '7', '1', 'year', '28'])
        writer.writerow(['C004', 'Physical Education', 'required_elective', 'T005|T006', '0', '3', 'quarter', '35'])
    elif template_type == 'periods':
        writer.writerow(['period_id', 'start_time', 'end_time'])
        # Add a sample row
        writer.writerow(['P001', '08:00', '08:45'])
        writer.writerow(['P002', '08:50', '09:35'])
    elif template_type == 'sections':
        writer.writerow(['course_id', 'section_number', 'teacher', 'period', 'room', 'max_size'])
        # Add a sample row
        writer.writerow(['C001', '1', 'T001', 'P001', 'R001', '30'])
        writer.writerow(['C001', '2', 'T002', 'P003', 'R002', '25'])
    
    return response

def view_students(request):
    """View all students in the database with filtering options."""
    # Get query parameters for filtering
    grade_filter = request.GET.get('grade', None)
    search_query = request.GET.get('search', '')
    
    # Start with all students
    students = Student.objects.all().order_by('grade_level', 'name')
    
    # Apply filters if provided
    if grade_filter and grade_filter.isdigit():
        students = students.filter(grade_level=int(grade_filter))
    
    if search_query:
        students = students.filter(name__icontains=search_query)
    
    # Group by grade level for easier viewing
    students_by_grade = {}
    for student in students:
        grade = student.grade_level
        if grade not in students_by_grade:
            students_by_grade[grade] = []
        students_by_grade[grade].append(student)
    
    # Sort grades
    sorted_grades = sorted(students_by_grade.keys())
    
    # Get students who have schedules
    scheduled_students = set()
    sections = Section.objects.all()
    for section in sections:
        for student_id in section.get_students_list():
            scheduled_students.add(student_id)
    
    context = {
        'students_by_grade': students_by_grade,
        'sorted_grades': sorted_grades,
        'grade_filter': grade_filter,
        'search_query': search_query,
        'total_students': students.count(),
        'scheduled_students': scheduled_students,
    }
    
    return render(request, 'schedule/view_students.html', context)

def student_detail(request, student_id):
    """View detailed information for a specific student."""
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        messages.error(request, "Student not found.")
        return redirect('view_students')
    
    # Get student's schedule
    sections = Section.objects.all().select_related('course', 'teacher', 'room', 'period')
    schedule = []
    
    for section in sections:
        if student_id in section.get_students_list():
            schedule.append(section)
    
    # Sort schedule by period
    schedule.sort(key=lambda s: (s.period.day, s.period.slot) if s.period else (99, 99))
    
    # Get all periods for organization
    periods = Period.objects.all().order_by('day', 'slot')
    period_dict = {}
    for period in periods:
        key = f"{period.get_day_display()}-{period.slot}"
        period_dict[key] = {'period': period, 'section': None}
    
    # Organize schedule by period
    for section in schedule:
        if section.period:
            key = f"{section.period.get_day_display()}-{section.period.slot}"
            if key in period_dict:
                period_dict[key]['section'] = section
    
    context = {
        'student': student,
        'schedule': schedule,
        'period_dict': period_dict,
        'has_schedule': bool(schedule)
    }
    
    return render(request, 'schedule/student_detail.html', context)

def edit_student(request, student_id):
    """Edit student information."""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f"Student {student.name} updated successfully.")
            return redirect('student_detail', student_id=student.id)
    else:
        form = StudentForm(instance=student)
    
    context = {
        'form': form,
        'student': student
    }
    
    return render(request, 'schedule/edit_student.html', context)

def delete_student(request, student_id):
    """Delete a student record."""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        # Save name for confirmation message
        student_name = student.name
        
        # Remove student from all sections
        sections = Section.objects.all()
        for section in sections:
            students_list = section.get_students_list()
            if student_id in students_list:
                students_list.remove(student_id)
                section.students = ','.join(students_list)
                section.save()
        
        # Delete the student
        student.delete()
        
        messages.success(request, f"Student {student_name} deleted successfully.")
        return redirect('view_students')
    
    # GET request - show confirmation page
    return render(request, 'schedule/delete_student_confirm.html', {'student': student})

def admin_reports(request):
    """View for administrative reports."""
    
    # Get enrollment by grade level
    students = Student.objects.all()
    enrollment_by_grade = {}
    total_students = 0
    
    for student in students:
        grade = student.grade_level
        if grade not in enrollment_by_grade:
            enrollment_by_grade[grade] = 0
        enrollment_by_grade[grade] += 1
        total_students += 1
    
    # Get enrollment by course
    course_enrollment = {}
    courses = Course.objects.all().order_by('grade_level', 'name')
    sections = Section.objects.all()
    
    for course in courses:
        course_enrollment[course.id] = {
            'course': course,
            'total_sections': 0,
            'total_students': 0,
            'avg_class_size': 0
        }
    
    for section in sections:
        course_id = section.course.id
        student_count = len(section.get_students_list())
        
        if course_id in course_enrollment:
            course_enrollment[course_id]['total_sections'] += 1
            course_enrollment[course_id]['total_students'] += student_count
    
    # Calculate averages
    for course_id, data in course_enrollment.items():
        if data['total_sections'] > 0:
            data['avg_class_size'] = round(data['total_students'] / data['total_sections'], 1)
    
    # Get teacher load
    teacher_load = {}
    teachers = Teacher.objects.all().order_by('name')
    
    for teacher in teachers:
        teacher_load[teacher.id] = {
            'teacher': teacher,
            'total_sections': 0,
            'total_students': 0,
            'courses': []
        }
    
    for section in sections:
        teacher_id = section.teacher.id
        student_count = len(section.get_students_list())
        
        if teacher_id in teacher_load:
            teacher_load[teacher_id]['total_sections'] += 1
            teacher_load[teacher_id]['total_students'] += student_count
            
            course_name = section.course.name
            if course_name not in teacher_load[teacher_id]['courses']:
                teacher_load[teacher_id]['courses'].append(course_name)
    
    context = {
        'enrollment_by_grade': enrollment_by_grade,
        'total_students': total_students,
        'course_enrollment': course_enrollment,
        'teacher_load': teacher_load,
    }
    
    return render(request, 'schedule/admin_reports.html', context)

# Helper functions for schedule generation
def generate_schedules():
    """Generate schedules for all students using constraint solver"""
    
    # Get all entities from the database
    students = Student.objects.all()
    teachers = Teacher.objects.all()
    rooms = Room.objects.all()
    periods = Period.objects.all()
    courses = Course.objects.all()
    
    # Create sections for core courses by grade level
    create_core_sections(courses, teachers, rooms, periods)
    
    # Assign students to core sections by grade level
    assign_students_to_core_sections(students)
    
    # Create sections for electives
    create_elective_sections(courses, teachers, rooms, periods)
    
    # Assign students to elective sections based on preferences
    assign_students_to_elective_sections(students)

def create_core_sections(courses, teachers, rooms, periods):
    """Create sections for core courses by grade level"""
    core_courses = courses.filter(type='core')
    
    for course in core_courses:
        # Get eligible teachers for this course
        eligible_teacher_ids = course.get_eligible_teachers_list()
        course_teachers = teachers.filter(id__in=eligible_teacher_ids)
        
        if not course_teachers:
            continue
        
        # Calculate number of sections needed based on grade level population
        student_count = Student.objects.filter(grade_level=course.grade_level).count()
        num_sections_needed = max(1, (student_count + course.max_students - 1) // course.max_students)
        
        # Create sections
        for i in range(num_sections_needed):
            # Find available teacher, room, period
            for teacher in course_teachers:
                for room in rooms.filter(capacity__gte=course.max_students):
                    for period in periods:
                        # Check if teacher and room are available in this period
                        if not Section.objects.filter(teacher=teacher, period=period).exists() and \
                           not Section.objects.filter(room=room, period=period).exists():
                            
                            # Create the section
                            Section.objects.create(
                                course=course,
                                teacher=teacher,
                                room=room,
                                period=period,
                                students=''
                            )
                            # Move to next section
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break

def assign_students_to_core_sections(students):
    """Assign students to core sections for their grade level"""
    for student in students:
        grade = student.grade_level
        
        # Find core courses for this grade
        core_sections = Section.objects.filter(
            course__type='core',
            course__grade_level=grade
        ).select_related('course', 'period')
        
        # Group by course type to ensure one section of each course
        course_sections = {}
        for section in core_sections:
            if section.course.id not in course_sections:
                course_sections[section.course.id] = []
            course_sections[section.course.id].append(section)
        
        # Assign student to one section of each course type
        for course_id, sections in course_sections.items():
            # Find a section that doesn't conflict with already assigned sections
            assigned_periods = []
            
            # Get periods of already assigned sections
            for assigned_section in Section.objects.filter(students__contains=student.id):
                assigned_periods.append(assigned_section.period_id)
            
            # Find a section with no conflict
            for section in sections:
                if section.period_id not in assigned_periods and \
                   len(section.get_students_list()) < section.course.max_students:
                    section.add_student(student.id)
                    break

def create_elective_sections(courses, teachers, rooms, periods):
    """Create sections for elective courses"""
    elective_courses = courses.filter(type__in=['elective', 'required_elective'])
    
    for course in elective_courses:
        # Get eligible teachers for this course
        eligible_teacher_ids = course.get_eligible_teachers_list()
        course_teachers = teachers.filter(id__in=eligible_teacher_ids)
        
        if not course_teachers:
            continue
        
        # Create at least one section per elective course
        for teacher in course_teachers:
            for room in rooms.filter(capacity__gte=course.max_students):
                for period in periods:
                    # Check if teacher and room are available in this period
                    if not Section.objects.filter(teacher=teacher, period=period).exists() and \
                       not Section.objects.filter(room=room, period=period).exists():
                        
                        # Create the section
                        Section.objects.create(
                            course=course,
                            teacher=teacher,
                            room=room,
                            period=period,
                            students=''
                        )
                        # One section is enough for now
                        break
                else:
                    continue
                break
            else:
                continue
            break

def assign_students_to_elective_sections(students):
    """Assign students to elective sections based on preferences"""
    
    # Process required electives first
    required_sections = Section.objects.filter(
        course__type='required_elective'
    ).select_related('course', 'period')
    
    for student in students:
        # Assign required electives
        assigned_periods = []
        
        # Get periods of already assigned sections
        for assigned_section in Section.objects.filter(students__contains=student.id):
            assigned_periods.append(assigned_section.period_id)
        
        # Assign one required elective of each type (e.g., PE)
        for section in required_sections:
            if section.period_id not in assigned_periods and \
               len(section.get_students_list()) < section.course.max_students:
                section.add_student(student.id)
                assigned_periods.append(section.period_id)
                break
    
    # Now process regular electives based on preferences
    for student in students:
        preferences = student.get_preferences_list()
        assigned_periods = []
        
        # Get periods of already assigned sections
        for assigned_section in Section.objects.filter(students__contains=student.id):
            assigned_periods.append(assigned_section.period_id)
        
        # Try to assign electives based on preferences
        for preference in preferences:
            # Find sections for this preference
            elective_sections = Section.objects.filter(
                course__type='elective',
                course__name__icontains=preference
            ).select_related('course', 'period')
            
            # Try to find a section that doesn't conflict
            for section in elective_sections:
                if section.period_id not in assigned_periods and \
                   len(section.get_students_list()) < section.course.max_students:
                    section.add_student(student.id)
                    assigned_periods.append(section.period_id)
                    break

def find_schedule_conflicts():
    """Find scheduling conflicts in the current schedule"""
    conflicts = []
    
    # Check for teacher conflicts (teaching multiple classes in same period)
    teachers = Teacher.objects.all()
    for teacher in teachers:
        sections = Section.objects.filter(teacher=teacher).select_related('period')
        period_counts = {}
        
        for section in sections:
            period_id = section.period_id
            if period_id in period_counts:
                period_counts[period_id].append(section)
            else:
                period_counts[period_id] = [section]
        
        for period_id, period_sections in period_counts.items():
            if len(period_sections) > 1:
                conflicts.append({
                    'type': 'teacher_conflict',
                    'teacher': teacher.name,
                    'period': period_sections[0].period.__str__(),
                    'sections': [s.course.name for s in period_sections]
                })
    
    # Check for room conflicts (multiple classes in same room/period)
    rooms = Room.objects.all()
    for room in rooms:
        sections = Section.objects.filter(room=room).select_related('period')
        period_counts = {}
        
        for section in sections:
            period_id = section.period_id
            if period_id in period_counts:
                period_counts[period_id].append(section)
            else:
                period_counts[period_id] = [section]
        
        for period_id, period_sections in period_counts.items():
            if len(period_sections) > 1:
                conflicts.append({
                    'type': 'room_conflict',
                    'room': room.number,
                    'period': period_sections[0].period.__str__(),
                    'sections': [s.course.name for s in period_sections]
                })
    
    # Check for student conflicts (assigned to multiple classes in same period)
    students = Student.objects.all()
    for student in students:
        student_id = student.id
        
        # Find all sections this student is in
        student_sections = []
        for section in Section.objects.filter(students__contains=student_id).select_related('period', 'course'):
            student_sections.append(section)
        
        period_counts = {}
        for section in student_sections:
            period_id = section.period_id
            if period_id in period_counts:
                period_counts[period_id].append(section)
            else:
                period_counts[period_id] = [section]
        
        for period_id, period_sections in period_counts.items():
            if len(period_sections) > 1:
                conflicts.append({
                    'type': 'student_conflict',
                    'student': student.name,
                    'period': period_sections[0].period.__str__(),
                    'sections': [s.course.name for s in period_sections]
                })
    
    return conflicts
