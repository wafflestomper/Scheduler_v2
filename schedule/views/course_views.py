from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from ..models import Course
from django.db import transaction
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
import csv
import io

from schedule.models import CourseGroup, Period


def view_courses(request):
    """View all courses."""
    courses = Course.objects.all().order_by('name')
    return render(request, 'schedule/view_courses.html', {'courses': courses})


def create_course(request):
    """Create a new course."""
    if request.method == 'POST':
        name = request.POST.get('name')
        course_type = request.POST.get('type')
        grade_level = request.POST.get('grade_level')
        max_students = request.POST.get('max_students', 30)  # Default capacity of 30
        sections_needed = request.POST.get('sections_needed', 1)  # Default 1 section
        
        try:
            # Validate input
            if not name:
                raise ValueError("Course name is required")
            
            if not course_type:
                raise ValueError("Course type is required")
            
            try:
                grade_level = int(grade_level)
            except (ValueError, TypeError):
                raise ValueError("Grade level must be a valid number")
            
            try:
                max_students = int(max_students)
                if max_students <= 0:
                    raise ValueError("Max students must be a positive number")
            except ValueError:
                raise ValueError("Max students must be a valid number")
            
            try:
                sections_needed = int(sections_needed)
                if sections_needed <= 0:
                    raise ValueError("Sections needed must be a positive number")
            except ValueError:
                raise ValueError("Sections needed must be a valid number")
            
            # Create the course
            with transaction.atomic():
                # Generate a course ID
                course_id = f"C{Course.objects.count() + 1:03d}"
                
                course = Course(
                    id=course_id,
                    name=name,
                    type=course_type,
                    grade_level=grade_level,
                    max_students=max_students,
                    sections_needed=sections_needed
                )
                course.save()
                
                messages.success(request, f"Course '{name}' created successfully!")
                return redirect('view_courses')
                
        except ValueError as e:
            messages.error(request, str(e))
            
    # For GET request or if there was an error in POST
    return render(request, 'schedule/create_course.html', {
        'course_types': Course.COURSE_TYPES
    })


def edit_course(request, course_id):
    """Edit an existing course."""
    course = get_object_or_404(Course, pk=course_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        course_type = request.POST.get('type')
        grade_level = request.POST.get('grade_level')
        max_students = request.POST.get('max_students')
        sections_needed = request.POST.get('sections_needed')
        
        try:
            # Validate input
            if not name:
                raise ValueError("Course name is required")
            
            if not course_type:
                raise ValueError("Course type is required")
            
            try:
                grade_level = int(grade_level)
            except (ValueError, TypeError):
                raise ValueError("Grade level must be a valid number")
            
            try:
                max_students = int(max_students)
                if max_students <= 0:
                    raise ValueError("Max students must be a positive number")
            except ValueError:
                raise ValueError("Max students must be a valid number")
            
            try:
                sections_needed = int(sections_needed)
                if sections_needed <= 0:
                    raise ValueError("Sections needed must be a positive number")
            except ValueError:
                raise ValueError("Sections needed must be a valid number")
            
            # Update the course
            with transaction.atomic():
                course.name = name
                course.type = course_type
                course.grade_level = grade_level
                course.max_students = max_students
                course.sections_needed = sections_needed
                course.save()
                
                messages.success(request, f"Course '{name}' updated successfully!")
                return redirect('view_courses')
                
        except ValueError as e:
            messages.error(request, str(e))
    
    # For GET request or if there was an error in POST
    return render(request, 'schedule/edit_course.html', {
        'course': course,
        'course_types': Course.COURSE_TYPES
    })


def delete_course(request, course_id):
    """Delete a course."""
    course = get_object_or_404(Course, pk=course_id)
    
    if request.method == 'POST':
        # Check if there are any sections using this course
        if course.sections.exists():
            messages.error(request, f"Cannot delete course '{course.name}' because it has sections assigned to it.")
            return redirect('view_courses')
        
        course_name = course.name
        course.delete()
        messages.success(request, f"Course '{course_name}' deleted successfully!")
        return redirect('view_courses')
    
    return render(request, 'schedule/delete_course_confirm.html', {'course': course})


def course_list(request):
    """View for listing all courses"""
    courses = Course.objects.all().order_by('grade_level', 'name')
    
    # Filter by grade level if provided
    grade_level = request.GET.get('grade_level')
    if grade_level:
        try:
            grade_level = int(grade_level)
            courses = courses.filter(grade_level=grade_level)
        except ValueError:
            # Invalid grade level, ignore filter
            pass
    
    # Filter by course type if provided
    course_type = request.GET.get('type')
    if course_type:
        courses = courses.filter(type=course_type)
    
    # Pagination
    paginator = Paginator(courses, 20)  # 20 courses per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'course_types': [choice[0] for choice in Course.COURSE_TYPES],
        'grade_level': grade_level,
        'course_type': course_type
    }
    
    return render(request, 'schedule/course_list.html', context)


def course_groups(request):
    """View for managing course groups (related language courses)"""
    groups = CourseGroup.objects.all().prefetch_related('courses').order_by('name')
    periods = Period.objects.all().order_by('slot')
    
    context = {
        'groups': groups,
        'periods': periods
    }
    
    return render(request, 'schedule/course_groups.html', context)


def create_course_group(request):
    """Handle creation of a new course group"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        period_id = request.POST.get('preferred_period')
        course_ids = request.POST.getlist('courses')
        
        if not name:
            messages.error(request, 'Group name is required')
            return redirect('course_groups')
        
        # Create group
        group = CourseGroup(
            name=name,
            description=description
        )
        
        # Set preferred period if provided
        if period_id:
            try:
                period = Period.objects.get(id=period_id)
                group.preferred_period = period
            except Period.DoesNotExist:
                pass
        
        group.save()
        
        # Add courses
        if course_ids:
            courses = Course.objects.filter(id__in=course_ids)
            group.courses.add(*courses)
        
        messages.success(request, f'Course group "{name}" created successfully')
        return redirect('course_groups')
    
    return redirect('course_groups')


def edit_course_group(request, group_id):
    """Handle editing of a course group"""
    group = get_object_or_404(CourseGroup, id=group_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        period_id = request.POST.get('preferred_period')
        course_ids = request.POST.getlist('courses')
        
        if not name:
            messages.error(request, 'Group name is required')
            return redirect('course_groups')
        
        # Update group
        group.name = name
        group.description = description
        
        # Set preferred period if provided
        if period_id:
            try:
                period = Period.objects.get(id=period_id)
                group.preferred_period = period
            except Period.DoesNotExist:
                group.preferred_period = None
        else:
            group.preferred_period = None
        
        group.save()
        
        # Update courses
        group.courses.clear()
        if course_ids:
            courses = Course.objects.filter(id__in=course_ids)
            group.courses.add(*courses)
        
        messages.success(request, f'Course group "{name}" updated successfully')
        return redirect('course_groups')
    
    courses = Course.objects.all().order_by('grade_level', 'name')
    periods = Period.objects.all().order_by('slot')
    
    context = {
        'group': group,
        'courses': courses,
        'periods': periods,
        'selected_course_ids': list(group.courses.values_list('id', flat=True))
    }
    
    return render(request, 'schedule/edit_course_group.html', context)


def delete_course_group(request, group_id):
    """Handle deletion of a course group"""
    group = get_object_or_404(CourseGroup, id=group_id)
    
    if request.method == 'POST':
        name = group.name
        group.delete()
        messages.success(request, f'Course group "{name}" deleted successfully')
    
    return redirect('course_groups') 