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
from ..services.csv_processors.processor_factory import ProcessorFactory
from ..services.template_service import TemplateService


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
                # Get processor for the specified data type
                try:
                    processor = ProcessorFactory.get_processor(data_type)
                except ValueError as e:
                    messages.error(request, str(e))
                    return render(request, self.template_name, {'form': form})
                    
                expected_headers = processor.get_expected_headers()
                
                if not all(header in headers for header in expected_headers):
                    missing_headers = [h for h in expected_headers if h not in headers]
                    messages.error(request, f'CSV file missing required headers: {", ".join(missing_headers)}')
                    return render(request, self.template_name, {'form': form})
                
                # Process the data using the appropriate processor
                try:
                    with transaction.atomic():
                        counts = processor.process_csv(reader)
                    
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
        try:
            processor = ProcessorFactory.get_processor(data_type)
            return processor.get_expected_headers()
        except ValueError:
            return []


def download_template_csv(request, template_type):
    """Download a template CSV file for a specific data type."""
    return TemplateService.get_template_csv(template_type) 