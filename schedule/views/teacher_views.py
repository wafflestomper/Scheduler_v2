from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from ..models import Teacher
from django.db import transaction


def view_teachers(request):
    """View all teachers."""
    teachers = Teacher.objects.all().order_by('name')
    return render(request, 'schedule/view_teachers.html', {'teachers': teachers})


def create_teacher(request):
    """Create a new teacher."""
    if request.method == 'POST':
        name = request.POST.get('name')
        availability = request.POST.get('availability')
        subjects = request.POST.get('subjects')
        
        try:
            # Validate input
            if not name:
                raise ValueError("Name is required")
            
            # Create the teacher
            with transaction.atomic():
                # Generate a teacher ID based on the name
                teacher_id = f"T{Teacher.objects.count() + 1:03d}"
                
                teacher = Teacher(
                    id=teacher_id,
                    name=name,
                    availability=availability if availability else "",
                    subjects=subjects if subjects else ""
                )
                teacher.save()
                
                messages.success(request, f"Teacher '{name}' created successfully!")
                return redirect('view_teachers')
                
        except ValueError as e:
            messages.error(request, str(e))
            
    # For GET request or if there was an error in POST
    return render(request, 'schedule/create_teacher.html')


def edit_teacher(request, teacher_id):
    """Edit an existing teacher."""
    teacher = get_object_or_404(Teacher, pk=teacher_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        availability = request.POST.get('availability')
        subjects = request.POST.get('subjects')
        
        try:
            # Validate input
            if not name:
                raise ValueError("Name is required")
            
            # Update the teacher
            with transaction.atomic():
                teacher.name = name
                teacher.availability = availability if availability else ""
                teacher.subjects = subjects if subjects else ""
                teacher.save()
                
                messages.success(request, f"Teacher '{name}' updated successfully!")
                return redirect('view_teachers')
                
        except ValueError as e:
            messages.error(request, str(e))
    
    # For GET request or if there was an error in POST
    return render(request, 'schedule/edit_teacher.html', {'teacher': teacher})


def delete_teacher(request, teacher_id):
    """Delete a teacher."""
    teacher = get_object_or_404(Teacher, pk=teacher_id)
    
    if request.method == 'POST':
        # Check if there are any sections assigned to this teacher
        if teacher.sections.exists():
            messages.error(request, f"Cannot delete teacher '{teacher.name}' because they have sections assigned to them.")
            return redirect('view_teachers')
        
        teacher_name = teacher.name
        teacher.delete()
        messages.success(request, f"Teacher '{teacher_name}' deleted successfully!")
        return redirect('view_teachers')
    
    return render(request, 'schedule/delete_teacher_confirm.html', {'teacher': teacher}) 