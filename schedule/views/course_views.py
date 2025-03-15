from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from ..models import Course
from django.db import transaction


def view_courses(request):
    """View all courses."""
    courses = Course.objects.all().order_by('name')
    return render(request, 'schedule/courses/view_courses.html', {'courses': courses})


def create_course(request):
    """Create a new course."""
    if request.method == 'POST':
        name = request.POST.get('name')
        course_type = request.POST.get('course_type')
        grade_level = request.POST.get('grade_level')
        capacity = request.POST.get('capacity', 30)  # Default capacity of 30
        sections_needed = request.POST.get('sections_needed', 1)  # Default 1 section
        
        try:
            # Validate input
            if not name:
                raise ValueError("Course name is required")
            
            if not course_type:
                raise ValueError("Course type is required")
            
            try:
                capacity = int(capacity)
                if capacity <= 0:
                    raise ValueError("Capacity must be a positive number")
            except ValueError:
                raise ValueError("Capacity must be a valid number")
            
            try:
                sections_needed = int(sections_needed)
                if sections_needed <= 0:
                    raise ValueError("Sections needed must be a positive number")
            except ValueError:
                raise ValueError("Sections needed must be a valid number")
            
            # Create the course
            with transaction.atomic():
                course = Course(
                    name=name,
                    course_type=course_type,
                    grade_level=grade_level,
                    capacity=capacity,
                    sections_needed=sections_needed
                )
                course.save()
                
                messages.success(request, f"Course '{name}' created successfully!")
                return redirect('view_courses')
                
        except ValueError as e:
            messages.error(request, str(e))
            
    # For GET request or if there was an error in POST
    return render(request, 'schedule/courses/create_course.html', {
        'course_types': Course.COURSE_TYPES
    })


def edit_course(request, course_id):
    """Edit an existing course."""
    course = get_object_or_404(Course, pk=course_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        course_type = request.POST.get('course_type')
        grade_level = request.POST.get('grade_level')
        capacity = request.POST.get('capacity')
        sections_needed = request.POST.get('sections_needed')
        
        try:
            # Validate input
            if not name:
                raise ValueError("Course name is required")
            
            if not course_type:
                raise ValueError("Course type is required")
            
            try:
                capacity = int(capacity)
                if capacity <= 0:
                    raise ValueError("Capacity must be a positive number")
            except ValueError:
                raise ValueError("Capacity must be a valid number")
            
            try:
                sections_needed = int(sections_needed)
                if sections_needed <= 0:
                    raise ValueError("Sections needed must be a positive number")
            except ValueError:
                raise ValueError("Sections needed must be a valid number")
            
            # Update the course
            with transaction.atomic():
                course.name = name
                course.course_type = course_type
                course.grade_level = grade_level
                course.capacity = capacity
                course.sections_needed = sections_needed
                course.save()
                
                messages.success(request, f"Course '{name}' updated successfully!")
                return redirect('view_courses')
                
        except ValueError as e:
            messages.error(request, str(e))
    
    # For GET request or if there was an error in POST
    return render(request, 'schedule/courses/edit_course.html', {
        'course': course,
        'course_types': Course.COURSE_TYPES
    })


def delete_course(request, course_id):
    """Delete a course."""
    course = get_object_or_404(Course, pk=course_id)
    
    if request.method == 'POST':
        # Check if there are any sections using this course
        if course.section_set.exists():
            messages.error(request, f"Cannot delete course '{course.name}' because it has sections assigned to it.")
            return redirect('view_courses')
        
        course_name = course.name
        course.delete()
        messages.success(request, f"Course '{course_name}' deleted successfully!")
        return redirect('view_courses')
    
    return render(request, 'schedule/courses/confirm_delete.html', {'course': course}) 