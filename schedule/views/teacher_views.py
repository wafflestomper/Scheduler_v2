from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from ..models import Teacher
from django.db import transaction


def view_teachers(request):
    """View all teachers."""
    teachers = Teacher.objects.all().order_by('last_name', 'first_name')
    return render(request, 'schedule/teachers/view_teachers.html', {'teachers': teachers})


def create_teacher(request):
    """Create a new teacher."""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        try:
            # Validate input
            if not first_name:
                raise ValueError("First name is required")
            
            if not last_name:
                raise ValueError("Last name is required")
            
            # Create the teacher
            with transaction.atomic():
                teacher = Teacher(
                    first_name=first_name,
                    last_name=last_name,
                    email=email if email else None
                )
                teacher.save()
                
                messages.success(request, f"Teacher '{first_name} {last_name}' created successfully!")
                return redirect('view_teachers')
                
        except ValueError as e:
            messages.error(request, str(e))
            
    # For GET request or if there was an error in POST
    return render(request, 'schedule/teachers/create_teacher.html')


def edit_teacher(request, teacher_id):
    """Edit an existing teacher."""
    teacher = get_object_or_404(Teacher, pk=teacher_id)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        try:
            # Validate input
            if not first_name:
                raise ValueError("First name is required")
            
            if not last_name:
                raise ValueError("Last name is required")
            
            # Update the teacher
            with transaction.atomic():
                teacher.first_name = first_name
                teacher.last_name = last_name
                teacher.email = email if email else None
                teacher.save()
                
                messages.success(request, f"Teacher '{first_name} {last_name}' updated successfully!")
                return redirect('view_teachers')
                
        except ValueError as e:
            messages.error(request, str(e))
    
    # For GET request or if there was an error in POST
    return render(request, 'schedule/teachers/edit_teacher.html', {'teacher': teacher})


def delete_teacher(request, teacher_id):
    """Delete a teacher."""
    teacher = get_object_or_404(Teacher, pk=teacher_id)
    
    if request.method == 'POST':
        # Check if there are any sections assigned to this teacher
        if teacher.section_set.exists():
            messages.error(request, f"Cannot delete teacher '{teacher.full_name}' because they have sections assigned to them.")
            return redirect('view_teachers')
        
        teacher_name = teacher.full_name
        teacher.delete()
        messages.success(request, f"Teacher '{teacher_name}' deleted successfully!")
        return redirect('view_teachers')
    
    return render(request, 'schedule/teachers/confirm_delete.html', {'teacher': teacher}) 