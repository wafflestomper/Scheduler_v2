from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.views import View
import csv
from io import StringIO
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Teacher, Room, Student, Course, Period, Section
from ..forms import CSVUploadForm


class CSVUploadView(View):
    """View for handling CSV uploads of various data types."""
    template_name = 'schedule/csv_upload.html'
    
    def get(self, request):
        # Get previously used data_type from session or use default
        data_type = request.session.get('last_data_type', None)
        initial_data = {'data_type': data_type} if data_type else {}
        form = CSVUploadForm(initial=initial_data)
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            data_type = form.cleaned_data['data_type']
            
            # Store the data_type in session to remember it for next time
            request.session['last_data_type'] = data_type
            
            # Check if file is CSV
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'File is not a CSV file. Please upload a file with .csv extension.')
                return render(request, self.template_name, {'form': form})
            
            # Read the file
            try:
                decoded_file = csv_file.read().decode('utf-8')
                io_string = StringIO(decoded_file)
                reader = csv.reader(io_string)
                
                # Get headers from first row
                headers = next(reader)
                
                # Validate headers based on data_type
                expected_headers = self.get_expected_headers(data_type)
                if not all(header in headers for header in expected_headers):
                    missing_headers = [h for h in expected_headers if h not in headers]
                    messages.error(request, f'CSV file missing required headers: {", ".join(missing_headers)}')
                    return render(request, self.template_name, {'form': form})
                
                # Process the data based on data_type
                try:
                    with transaction.atomic():
                        if data_type == 'students':
                            counts = self.process_students(reader)
                        elif data_type == 'teachers':
                            counts = self.process_teachers(reader)
                        elif data_type == 'rooms':
                            counts = self.process_rooms(reader)
                        elif data_type == 'courses':
                            counts = self.process_courses(reader)
                        elif data_type == 'periods':
                            counts = self.process_periods(reader)
                        elif data_type == 'sections':
                            counts = self.process_sections(reader)
                        else:
                            messages.error(request, f'Unknown data type: {data_type}')
                            return render(request, self.template_name, {'form': form})
                    
                    if 'created' in counts and 'updated' in counts:
                        messages.success(request, f'Successfully processed {data_type} data: {counts["created"]} created, {counts["updated"]} updated.')
                        
                        # Display any errors that occurred during processing
                        if 'errors' in counts and counts['errors']:
                            for error in counts['errors'][:10]:  # Limit to first 10 errors to avoid overwhelming the user
                                messages.warning(request, error)
                            
                            if len(counts['errors']) > 10:
                                messages.warning(request, f'... and {len(counts["errors"]) - 10} more errors. Check the console for details.')
                                
                            # Also print errors to console for debugging
                            print(f"\nErrors during {data_type} processing:")
                            for error in counts['errors']:
                                print(f"  - {error}")
                        
                    elif 'processed' in counts:
                        messages.success(request, f'Successfully processed {counts["processed"]} {data_type}.')
                    else:
                        messages.success(request, f'Successfully processed {data_type} data.')
                        
                except ValidationError as e:
                    messages.error(request, f'Validation error: {str(e)}')
                    return render(request, self.template_name, {'form': form})
                except Exception as e:
                    messages.error(request, f'Error processing CSV: {str(e)}')
                    return render(request, self.template_name, {'form': form})
                
                return redirect('index')
                
            except Exception as e:
                messages.error(request, f'Error reading CSV file: {str(e)}')
                return render(request, self.template_name, {'form': form})
        
        return render(request, self.template_name, {'form': form})
    
    def get_expected_headers(self, data_type):
        """Get expected headers for different data types."""
        if data_type == 'students':
            return ['student_id', 'first_name', 'nickname', 'last_name', 'grade_level']
        elif data_type == 'teachers':
            return ['teacher_id', 'first_name', 'last_name', 'availability', 'subjects']
        elif data_type == 'rooms':
            return ['room_id', 'number', 'capacity', 'type']
        elif data_type == 'courses':
            return ['course_id', 'name', 'course_type', 'eligible_teachers', 'grade_level', 'sections_needed', 'duration']
        elif data_type == 'periods':
            return ['period_id', 'period_name', 'days', 'slot', 'start_time', 'end_time']
        elif data_type == 'sections':
            return ['course', 'section_number', 'teacher', 'period', 'room', 'max_size', 'when']
        return []
    
    def process_students(self, reader):
        """Process students data from CSV."""
        created, updated, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):  # Start from 2 for line number (after header)
            try:
                if not any(row):  # Skip empty rows
                    continue
                    
                # Get field values based on CSV column order
                student_id = row[0].strip() if len(row) > 0 else None
                first_name = row[1].strip() if len(row) > 1 else None
                nickname = row[2].strip() if len(row) > 2 else None
                last_name = row[3].strip() if len(row) > 3 else None
                grade_level = int(row[4].strip()) if len(row) > 4 and row[4].strip() else None
                
                # Validate required fields
                if not student_id:
                    errors.append(f'Line {i}: Missing student ID')
                    continue
                
                if not first_name:
                    errors.append(f'Line {i}: Missing first name')
                    continue
                    
                if not last_name:
                    errors.append(f'Line {i}: Missing last name')
                    continue
                
                # Construct full name
                name = f"{first_name} {last_name}"
                if nickname:
                    name = f"{first_name} '{nickname}' {last_name}"
                
                # Check if student exists
                try:
                    student = Student.objects.get(id=student_id)
                    # Update existing student
                    student.name = name
                    student.grade_level = grade_level
                    student.save()
                    updated += 1
                except Student.DoesNotExist:
                    # Create new student
                    Student.objects.create(
                        id=student_id,
                        name=name,
                        grade_level=grade_level
                    )
                    created += 1
            except Exception as e:
                errors.append(f'Line {i}: Error processing student: {str(e)}')
        
        return {'created': created, 'updated': updated, 'errors': errors}
    
    def process_teachers(self, reader):
        """Process teachers data from CSV."""
        created, updated, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):  # Start from 2 for line number (after header)
            try:
                if not any(row):  # Skip empty rows
                    continue
                
                # Get field values based on CSV column order
                teacher_id = row[0].strip() if len(row) > 0 else None
                first_name = row[1].strip() if len(row) > 1 else None
                last_name = row[2].strip() if len(row) > 2 else None
                availability = row[3].strip() if len(row) > 3 and row[3].strip() else ""
                subjects = row[4].strip() if len(row) > 4 and row[4].strip() else ""
                
                # Validate required fields
                if not teacher_id:
                    errors.append(f'Line {i}: Missing teacher ID')
                    continue
                
                if not first_name:
                    errors.append(f'Line {i}: Missing first name')
                    continue
                    
                if not last_name:
                    errors.append(f'Line {i}: Missing last name')
                    continue
                
                # Construct full name
                name = f"{first_name} {last_name}"
                
                # Check if teacher exists
                try:
                    teacher = Teacher.objects.get(id=teacher_id)
                    # Update existing teacher
                    teacher.name = name
                    teacher.availability = availability
                    teacher.subjects = subjects
                    teacher.save()
                    updated += 1
                except Teacher.DoesNotExist:
                    # Create new teacher
                    Teacher.objects.create(
                        id=teacher_id,
                        name=name,
                        availability=availability,
                        subjects=subjects
                    )
                    created += 1
            except Exception as e:
                errors.append(f'Line {i}: Error processing teacher: {str(e)}')
        
        return {'created': created, 'updated': updated, 'errors': errors}
    
    def process_rooms(self, reader):
        """Process rooms data from CSV."""
        created, updated, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):  # Start from 2 for line number (after header)
            try:
                if not any(row):  # Skip empty rows
                    continue
                    
                # Get field values
                room_id = row[0].strip() if len(row) > 0 else None
                number = row[1].strip() if len(row) > 1 else None
                capacity = int(row[2].strip()) if len(row) > 2 and row[2].strip() else 30
                room_type = row[3].strip() if len(row) > 3 and row[3].strip() else 'classroom'
                
                # Validate required fields
                if not room_id:
                    errors.append(f'Line {i}: Missing room ID')
                    continue
                
                if not number:
                    errors.append(f'Line {i}: Missing room number')
                    continue
                
                # Check if room exists
                try:
                    room = Room.objects.get(id=room_id)
                    # Update existing room
                    room.number = number
                    room.capacity = capacity
                    room.type = room_type
                    room.save()
                    updated += 1
                except Room.DoesNotExist:
                    # Create new room
                    Room.objects.create(
                        id=room_id,
                        number=number,
                        capacity=capacity,
                        type=room_type
                    )
                    created += 1
            except Exception as e:
                errors.append(f'Line {i}: Error processing room: {str(e)}')
        
        return {'created': created, 'updated': updated, 'errors': errors}
    
    def process_courses(self, reader):
        """Process courses data from CSV."""
        created, updated, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):  # Start from 2 for line number (after header)
            try:
                if not any(row):  # Skip empty rows
                    continue
                
                # Get field values
                course_id = row[0].strip() if len(row) > 0 else None
                name = row[1].strip() if len(row) > 1 else None
                course_type = row[2].strip() if len(row) > 2 else None
                teachers = row[3].strip() if len(row) > 3 and row[3].strip() else ''
                grade_level = int(row[4].strip()) if len(row) > 4 and row[4].strip() else 0
                sections_needed = int(row[5].strip()) if len(row) > 5 and row[5].strip() else 1
                duration = row[6].strip() if len(row) > 6 and row[6].strip() else 'year'
                
                # Validate required fields
                if not course_id:
                    errors.append(f'Line {i}: Missing course ID')
                    continue
                
                if not name:
                    errors.append(f'Line {i}: Missing course name')
                    continue
                
                if not course_type:
                    errors.append(f'Line {i}: Missing course type')
                    continue
                
                # Check if course exists
                try:
                    course = Course.objects.get(id=course_id)
                    # Update existing course
                    course.name = name
                    course.type = course_type
                    course.eligible_teachers = teachers
                    course.grade_level = grade_level
                    course.sections_needed = sections_needed
                    course.duration = duration
                    course.save()
                    updated += 1
                except Course.DoesNotExist:
                    # Create new course
                    Course.objects.create(
                        id=course_id,
                        name=name,
                        type=course_type,
                        eligible_teachers=teachers,
                        grade_level=grade_level,
                        sections_needed=sections_needed,
                        duration=duration
                    )
                    created += 1
            except Exception as e:
                errors.append(f'Line {i}: Error processing course: {str(e)}')
        
        return {'created': created, 'updated': updated, 'errors': errors}
    
    def process_periods(self, reader):
        """Process periods data from CSV."""
        created, updated, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):  # Start from 2 for line number (after header)
            try:
                if not any(row):  # Skip empty rows
                    continue
                    
                # Get field values
                period_id = row[0].strip() if len(row) > 0 else None
                period_name = row[1].strip() if len(row) > 1 else None
                days = row[2].strip() if len(row) > 2 and row[2].strip() else 'M'
                slot = row[3].strip() if len(row) > 3 and row[3].strip() else None
                start_time = row[4].strip() if len(row) > 4 and row[4].strip() else None
                end_time = row[5].strip() if len(row) > 5 and row[5].strip() else None
                
                # Validate required fields
                if not period_id:
                    errors.append(f'Line {i}: Missing period ID')
                    continue
                
                if not slot:
                    errors.append(f'Line {i}: Missing period slot')
                    continue
                
                if not start_time:
                    errors.append(f'Line {i}: Missing start time')
                    continue
                
                if not end_time:
                    errors.append(f'Line {i}: Missing end time')
                    continue
                
                # Check if period exists
                try:
                    period = Period.objects.get(id=period_id)
                    # Update existing period
                    period.period_name = period_name
                    period.days = days
                    period.slot = slot
                    period.start_time = start_time
                    period.end_time = end_time
                    period.save()
                    updated += 1
                except Period.DoesNotExist:
                    # Create new period
                    Period.objects.create(
                        id=period_id,
                        period_name=period_name,
                        days=days,
                        slot=slot,
                        start_time=start_time,
                        end_time=end_time
                    )
                    created += 1
            except Exception as e:
                errors.append(f'Line {i}: Error processing period: {str(e)}')
        
        return {'created': created, 'updated': updated, 'errors': errors}
    
    def process_sections(self, reader):
        """Process sections data from CSV."""
        created, updated, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):  # Start from 2 for line number (after header)
            try:
                if not any(row):  # Skip empty rows
                    continue
                    
                # Get field values
                course_id = row[0].strip() if len(row) > 0 else None
                section_number = row[1].strip() if len(row) > 1 and row[1].strip() else '1'
                teacher_id = row[2].strip() if len(row) > 2 and row[2].strip() else None
                period_id = row[3].strip() if len(row) > 3 and row[3].strip() else None
                room_id = row[4].strip() if len(row) > 4 and row[4].strip() else None
                max_size = int(row[5].strip()) if len(row) > 5 and row[5].strip() else 30  # Default to 30
                when = row[6].strip() if len(row) > 6 and row[6].strip() else 'year'
                
                # Validate required fields
                if not course_id:
                    errors.append(f'Line {i}: Missing course ID')
                    continue
                
                # Get related objects
                try:
                    course = Course.objects.get(id=course_id)
                except Course.DoesNotExist:
                    errors.append(f'Line {i}: Course with ID {course_id} does not exist')
                    continue
                
                teacher = None
                if teacher_id:
                    try:
                        teacher = Teacher.objects.get(id=teacher_id)
                    except Teacher.DoesNotExist:
                        errors.append(f'Line {i}: Teacher with ID {teacher_id} does not exist')
                        continue
                
                period = None
                if period_id:
                    try:
                        period = Period.objects.get(id=period_id)
                    except Period.DoesNotExist:
                        errors.append(f'Line {i}: Period with ID {period_id} does not exist')
                        continue
                
                room = None
                if room_id:
                    try:
                        room = Room.objects.get(id=room_id)
                    except Room.DoesNotExist:
                        errors.append(f'Line {i}: Room with ID {room_id} does not exist')
                        continue
                
                # Generate a unique ID for the section
                section_id = f"{course_id}-{section_number}"
                
                # Create or update section
                try:
                    # Try to find an existing section by ID
                    try:
                        section = Section.objects.get(id=section_id)
                        # Update existing section
                        section.course = course
                        section.section_number = int(section_number)
                        if teacher:
                            section.teacher = teacher
                        if period:
                            section.period = period
                        if room:
                            section.room = room
                        section.max_size = max_size
                        section.when = when
                        section.save()
                        updated += 1
                    except Section.DoesNotExist:
                        # Create new section
                        Section.objects.create(
                            id=section_id,
                            course=course,
                            section_number=int(section_number),
                            teacher=teacher,
                            period=period,
                            room=room,
                            max_size=max_size,
                            when=when
                        )
                        created += 1
                except Exception as e:
                    errors.append(f'Line {i}: Error processing section: {str(e)}')
            except Exception as e:
                errors.append(f'Line {i}: Error processing section: {str(e)}')
        
        return {'created': created, 'updated': updated, 'errors': errors}


def download_template_csv(request, template_type):
    """Download a template CSV file for a specific data type."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{template_type}_template.csv"'
    
    writer = csv.writer(response)
    
    if template_type == 'students':
        writer.writerow(['first_name', 'last_name', 'grade', 'email'])
        writer.writerow(['John', 'Doe', '9', 'john.doe@example.com'])
        writer.writerow(['Jane', 'Smith', '10', 'jane.smith@example.com'])
    
    elif template_type == 'teachers':
        writer.writerow(['first_name', 'last_name', 'email'])
        writer.writerow(['Robert', 'Johnson', 'robert.johnson@example.com'])
        writer.writerow(['Sarah', 'Williams', 'sarah.williams@example.com'])
    
    elif template_type == 'rooms':
        writer.writerow(['name', 'capacity', 'room_type'])
        writer.writerow(['Room 101', '30', 'Classroom'])
        writer.writerow(['Science Lab', '25', 'Lab'])
    
    elif template_type == 'courses':
        writer.writerow(['course_id', 'name', 'course_type', 'teachers', 'grade_level', 'sections_needed', 'duration'])
        writer.writerow(['C001', 'Algebra I', 'core', 'T001|T002', '9', '2', 'year'])
        writer.writerow(['C002', 'Biology', 'elective', 'T003', '10', '3', 'trimester'])
    
    elif template_type == 'periods':
        writer.writerow(['name', 'start_time', 'end_time'])
        writer.writerow(['Period 1', '08:00', '08:50'])
        writer.writerow(['Period 2', '09:00', '09:50'])
    
    elif template_type == 'sections':
        writer.writerow(['course', 'section_number', 'teacher', 'period', 'room', 'max_size', 'when'])
        writer.writerow(['C001', '1', 'T001', 'P001', 'R001', '25', 'year'])
        writer.writerow(['C002', '1', '', 'P002', '', '', 'trimester'])  # Example with optional fields blank
    
    else:
        return HttpResponse(f"Unknown template type: {template_type}", status=400)
    
    return response 