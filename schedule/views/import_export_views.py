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
            return ['name', 'course_type', 'grade_level', 'capacity', 'sections_needed']
        elif data_type == 'periods':
            return ['name', 'start_time', 'end_time']
        elif data_type == 'sections':
            return ['course_id', 'teacher_id', 'room_id', 'period_id']
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
                
            name = row[0].strip()
            course_type = row[1].strip()
            grade_level = row[2].strip() if row[2].strip() else None
            capacity = int(row[3].strip()) if row[3].strip() else 30
            sections_needed = int(row[4].strip()) if len(row) > 4 and row[4].strip() else 1
            
            # Check if course exists
            course, created_flag = Course.objects.update_or_create(
                name=name,
                defaults={
                    'course_type': course_type,
                    'grade_level': grade_level,
                    'capacity': capacity,
                    'sections_needed': sections_needed
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
        for row in reader:
            if not any(row):  # Skip empty rows
                continue
                
            course_id = int(row[0].strip()) if row[0].strip() else None
            teacher_id = int(row[1].strip()) if row[1].strip() else None
            room_id = int(row[2].strip()) if row[2].strip() else None
            period_id = int(row[3].strip()) if row[3].strip() else None
            
            # Get related objects or None
            course = Course.objects.get(pk=course_id) if course_id else None
            teacher = Teacher.objects.get(pk=teacher_id) if teacher_id else None
            room = Room.objects.get(pk=room_id) if room_id else None
            period = Period.objects.get(pk=period_id) if period_id else None
            
            # We need at least a course to create a section
            if not course:
                continue
            
            # Create a unique identifier for this section
            # If a section with these attributes already exists, we'll update it
            section, created_flag = Section.objects.update_or_create(
                course=course,
                teacher=teacher,
                room=room,
                period=period
            )
            
            if created_flag:
                created += 1
            else:
                updated += 1
        
        return {'created': created, 'updated': updated}


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
        writer.writerow(['name', 'course_type', 'grade_level', 'capacity', 'sections_needed'])
        writer.writerow(['Algebra I', 'Math', '9', '30', '2'])
        writer.writerow(['Biology', 'Science', '10', '25', '3'])
    
    elif template_type == 'periods':
        writer.writerow(['name', 'start_time', 'end_time'])
        writer.writerow(['Period 1', '08:00', '08:50'])
        writer.writerow(['Period 2', '09:00', '09:50'])
    
    elif template_type == 'sections':
        writer.writerow(['course_id', 'teacher_id', 'room_id', 'period_id'])
        writer.writerow(['1', '1', '1', '1'])
        writer.writerow(['2', '2', '2', '2'])
    
    else:
        return HttpResponse(f"Unknown template type: {template_type}", status=400)
    
    return response 