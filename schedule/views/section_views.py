from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from ..models import Section, Course, Teacher, Room, Period
from ..services.section_services.section_service import SectionService
from ..services.section_services.conflict_service import ConflictService
from ..services.section_services.export_service import ExportService
from ..services.section_services.schedule_service import ScheduleService


def edit_section(request, section_id):
    """Edit an existing section."""
    section = SectionService.get_section_by_id(section_id)
    
    if request.method == 'POST':
        try:
            # Update section with form data
            data = {
                'teacher_id': request.POST.get('teacher_id'),
                'room_id': request.POST.get('room_id'),
                'period_id': request.POST.get('period_id'),
                'max_size': request.POST.get('max_size'),
                'exact_size': request.POST.get('exact_size')
            }
            
            SectionService.update_section(section_id, data)
            messages.success(request, f"Section '{section_id}' has been updated.")
            return redirect('view_sections')
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('edit_section', section_id=section_id)
        
    # Get all teachers, rooms, and periods for the form
    teachers = Teacher.objects.all().order_by('name')
    rooms = Room.objects.all().order_by('number')
    periods = Period.objects.all().order_by('slot')
    
    context = {
        'section': section,
        'teachers': teachers,
        'rooms': rooms,
        'periods': periods,
    }
    
    return render(request, 'schedule/edit_section.html', context)


def get_conflicts(request):
    """Get conflicts for visualization."""
    conflicts = ConflictService.find_all_conflicts()
    return JsonResponse(conflicts, safe=False)


def export_master_schedule(request):
    """Export the master schedule to a CSV file."""
    return ExportService.export_master_schedule()


def master_schedule(request):
    """Display the master schedule."""
    result = ScheduleService.get_master_schedule()
    return render(request, 'schedule/master_schedule.html', result)


def student_schedules(request):
    """Display student schedules."""
    student_id = request.GET.get('student_id')
    
    if student_id:
        # Display a specific student's schedule
        result = ScheduleService.get_student_schedule(student_id)
        return render(request, 'schedule/student_schedules.html', result)
    else:
        # Display a list of all students with their section counts
        result = ScheduleService.get_all_student_schedules_summary()
        return render(request, 'schedule/student_schedules.html', result)


def section_roster(request, section_id):
    """Display the roster of students for a section."""
    result = SectionService.get_section_roster(section_id)
    return render(request, 'schedule/section_roster.html', result)


def check_conflicts(request, section_id):
    """Check for conflicts for a specific section."""
    section = get_object_or_404(Section, pk=section_id)
    conflicts = ConflictService.check_section_conflicts(section)
    return JsonResponse(conflicts)


def view_sections(request):
    """View all sections."""
    result = SectionService.get_all_sections_by_course()
    return render(request, 'schedule/view_sections.html', result)


def add_section(request):
    """Add a new section."""
    if request.method == 'POST':
        try:
            # Create section with form data
            data = {
                'course': request.POST.get('course'),
                'teacher': request.POST.get('teacher'),
                'room': request.POST.get('room'),
                'period': request.POST.get('period'),
                'section_number': request.POST.get('section_number', 1),
                'max_size': request.POST.get('max_size'),
                'exact_size': request.POST.get('exact_size'),
                'when': request.POST.get('when', 'year')
            }
            
            section = SectionService.create_section(data)
            messages.success(request, f"Section {section.id} has been created.")
            return redirect('view_sections')
            
        except ValueError as e:
            messages.error(request, str(e))
            
        except Exception as e:
            messages.error(request, f"Error creating section: {str(e)}")
    
    # Get all courses, teachers, rooms, and periods for the form
    courses = Course.objects.all().order_by('name')
    teachers = Teacher.objects.all().order_by('name')
    rooms = Room.objects.all().order_by('number')
    periods = Period.objects.all().order_by('slot')
    
    context = {
        'courses': courses,
        'teachers': teachers,
        'rooms': rooms,
        'periods': periods,
    }
    
    return render(request, 'schedule/add_section.html', context)


def delete_section(request, section_id):
    """Delete a section."""
    section = SectionService.get_section_by_id(section_id)
    
    if request.method == 'POST':
        try:
            SectionService.delete_section(section_id)
            messages.success(request, f"Section {section_id} has been deleted.")
            return redirect('view_sections')
        except Exception as e:
            messages.error(request, f"Error deleting section: {str(e)}")
            return redirect('view_sections')
    
    # Confirmation page
    context = {
        'section': section,
        'student_count': section.students.count()
    }
    
    return render(request, 'schedule/delete_section_confirm.html', context) 