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
            return ['first_name', 'last_name', 'grade', 'email']
        elif data_type == 'teachers':
            return ['first_name', 'last_name', 'email']
        elif data_type == 'rooms':
            return ['name', 'capacity', 'room_type']
        elif data_type == 'courses':
            return ['course_id', 'name', 'course_type', 'teachers', 'grade_level', 'sections_needed', 'duration']
        elif data_type == 'periods':
            return ['name', 'start_time', 'end_time']
        elif data_type == 'sections':
            return ['section_id', 'course', 'section_number', 'teacher', 'period', 'room', 'max_size', 'exact_size', 'when']
        return []
    
    def process_students(self, reader):
        """Process students data from CSV."""
        created, updated = 0, 0
        for row in reader:
            if not any(row):  # Skip empty rows
                continue
                
            first_name = row[0].strip()
            last_name = row[1].strip()
            grade = int(row[2].strip()) if row[2].strip() else None
            email = row[3].strip() if len(row) > 3 and row[3].strip() else None
            
            # Check if student exists
            student, created_flag = Student.objects.update_or_create(
                first_name=first_name,
                last_name=last_name,
                defaults={'grade': grade, 'email': email}
            )
            
            if created_flag:
                created += 1
            else:
                updated += 1
        
        return {'created': created, 'updated': updated}
    
    def process_teachers(self, reader):
        """Process teachers data from CSV."""
        created, updated = 0, 0
        for row in reader:
            if not any(row):  # Skip empty rows
                continue
                
            first_name = row[0].strip()
            last_name = row[1].strip()
            email = row[2].strip() if len(row) > 2 and row[2].strip() else None
            
            # Check if teacher exists
            teacher, created_flag = Teacher.objects.update_or_create(
                first_name=first_name,
                last_name=last_name,
                defaults={'email': email}
            )
            
            if created_flag:
                created += 1
            else:
                updated += 1
        
        return {'created': created, 'updated': updated}
    
    def process_rooms(self, reader):
        """Process rooms data from CSV."""
        created, updated = 0, 0
        for row in reader:
            if not any(row):  # Skip empty rows
                continue
                
            name = row[0].strip()
            capacity = int(row[1].strip()) if row[1].strip() else 30
            room_type = row[2].strip() if len(row) > 2 and row[2].strip() else ''
            
            # Check if room exists
            room, created_flag = Room.objects.update_or_create(
                name=name,
                defaults={'capacity': capacity, 'room_type': room_type}
            )
            
            if created_flag:
                created += 1
            else:
                updated += 1
        
        return {'created': created, 'updated': updated}
    
    def process_courses(self, reader):
        """Process courses data from CSV."""
        created, updated = 0, 0
        for row in reader:
            if not any(row):  # Skip empty rows
                continue
            
            course_id = row[0].strip() if row[0].strip() else None
            name = row[1].strip()
            course_type = row[2].strip()
            teachers = row[3].strip() if len(row) > 3 else ''
            grade_level = int(row[4].strip()) if len(row) > 4 and row[4].strip() else 0
            sections_needed = int(row[5].strip()) if len(row) > 5 and row[5].strip() else 1
            duration = row[6].strip() if len(row) > 6 and row[6].strip() else 'year'
            
            # Check if course exists
            course, created_flag = Course.objects.update_or_create(
                id=course_id,
                defaults={
                    'name': name,
                    'type': course_type,
                    'eligible_teachers': teachers,
                    'grade_level': grade_level,
                    'sections_needed': sections_needed,
                    'duration': duration
                }
            )
            
            if created_flag:
                created += 1
            else:
                updated += 1
        
        return {'created': created, 'updated': updated}
    
    def process_periods(self, reader):
        """Process periods data from CSV."""
        created, updated = 0, 0
        for row in reader:
            if not any(row):  # Skip empty rows
                continue
                
            name = row[0].strip()
            start_time = row[1].strip()
            end_time = row[2].strip()
            
            # Check if period exists
            period, created_flag = Period.objects.update_or_create(
                name=name,
                defaults={'start_time': start_time, 'end_time': end_time}
            )
            
            if created_flag:
                created += 1
            else:
                updated += 1
        
        return {'created': created, 'updated': updated}
    
    def process_sections(self, reader):
        """Process sections data from CSV."""
        created, updated = 0, 0
        errors = []
        
        for row_index, row in enumerate(reader, start=1):
            if not any(row):  # Skip empty rows
                continue
                
            section_id = row[0].strip() if row[0].strip() else None
            course_id = row[1].strip() if len(row) > 1 and row[1].strip() else None
            section_number = row[2].strip() if len(row) > 2 and row[2].strip() else '1'
            teacher = row[3].strip() if len(row) > 3 and row[3].strip() else None
            period = row[4].strip() if len(row) > 4 and row[4].strip() else None
            room = row[5].strip() if len(row) > 5 and row[5].strip() else None
            max_size = row[6].strip() if len(row) > 6 and row[6].strip() else None
            exact_size = row[7].strip() if len(row) > 7 and row[7].strip() else None
            when = row[8].strip() if len(row) > 8 and row[8].strip() else 'year'
            
            # Convert max_size to integer if provided
            if max_size:
                try:
                    max_size = int(max_size)
                except ValueError:
                    errors.append(f"Row {row_index}: max_size must be a number, got '{max_size}'")
                    max_size = None
                    
            # Convert exact_size to integer if provided
            if exact_size:
                try:
                    exact_size = int(exact_size)
                except ValueError:
                    errors.append(f"Row {row_index}: exact_size must be a number, got '{exact_size}'")
                    exact_size = None
            
            # Get related objects or None
            try:
                # Course is required
                if not course_id:
                    errors.append(f"Row {row_index}: Course ID is required")
                    continue
                    
                try:
                    course = Course.objects.get(pk=course_id)
                except Course.DoesNotExist:
                    errors.append(f"Row {row_index}: Course with ID '{course_id}' does not exist")
                    continue
                
                # These are optional and can be None
                teacher_obj = None
                room_obj = None
                
                # Only try to get teacher or room if values were provided
                if teacher:
                    try:
                        teacher_obj = Teacher.objects.get(pk=teacher)
                    except Teacher.DoesNotExist:
                        errors.append(f"Row {row_index}: Teacher with ID '{teacher}' does not exist")
                
                if room:
                    try:
                        room_obj = Room.objects.get(pk=room)
                    except Room.DoesNotExist:
                        errors.append(f"Row {row_index}: Room with ID '{room}' does not exist")
                
                # Period is required
                try:
                    period_obj = Period.objects.get(pk=period) if period else None
                    if not period_obj:
                        errors.append(f"Row {row_index}: Period is required")
                        continue
                except Period.DoesNotExist:
                    errors.append(f"Row {row_index}: Period with ID '{period}' does not exist")
                    continue
                
                # Create or update the section
                try:
                    section_number_int = int(section_number)
                except ValueError:
                    errors.append(f"Row {row_index}: section_number must be a number, got '{section_number}'")
                    continue
                
                # Create or update the section
                if section_id:
                    # If section_id is provided, use it
                    section = Section(
                        id=section_id,
                        course=course,
                        section_number=section_number_int,
                        teacher=teacher_obj,
                        period=period_obj,
                        room=room_obj,
                        max_size=max_size,
                        exact_size=exact_size,
                        when=when
                    )
                else:
                    # If no section_id provided, create one from course_id and section_number
                    new_section_id = f"{course_id}-{section_number}"
                    section = Section(
                        id=new_section_id,
                        course=course,
                        section_number=section_number_int,
                        teacher=teacher_obj,
                        period=period_obj,
                        room=room_obj,
                        max_size=max_size,
                        exact_size=exact_size,
                        when=when
                    )
                
                section.save()
                
                if section_id:
                    created += 1
                else:
                    updated += 1
                    
            except Exception as e:
                errors.append(f"Row {row_index}: Unexpected error: {str(e)}")
                continue
        
        result = {'created': created, 'updated': updated}
        if errors:
            result['errors'] = errors
        return result


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
        writer.writerow(['section_id', 'course', 'section_number', 'teacher', 'period', 'room', 'max_size', 'exact_size', 'when'])
        writer.writerow(['S001', 'C001', '1', 'T001', 'P001', 'R001', '25', '25', 'year'])
        writer.writerow(['S002', 'C002', '1', '', 'P002', '', '', '', 'trimester'])  # Example with optional fields blank
    
    else:
        return HttpResponse(f"Unknown template type: {template_type}", status=400)
    
    return response 