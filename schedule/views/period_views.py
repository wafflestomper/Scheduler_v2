from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from ..models import Period
from django.db import transaction


def view_periods(request):
    """View all periods."""
    periods = Period.objects.all().order_by('start_time')
    return render(request, 'schedule/periods/view_periods.html', {'periods': periods})


def create_period(request):
    """Create a new period."""
    if request.method == 'POST':
        name = request.POST.get('name')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        try:
            # Validate input
            if not name:
                raise ValueError("Period name is required")
            
            if not start_time:
                raise ValueError("Start time is required")
            
            if not end_time:
                raise ValueError("End time is required")
            
            # Validate that start_time comes before end_time
            from datetime import datetime
            
            try:
                start_datetime = datetime.strptime(start_time, '%H:%M')
                end_datetime = datetime.strptime(end_time, '%H:%M')
                
                if start_datetime >= end_datetime:
                    raise ValueError("End time must be after start time")
            except ValueError as e:
                if "unconverted data remains" in str(e) or "does not match format" in str(e):
                    raise ValueError("Time must be in 24-hour format (HH:MM)")
                else:
                    raise
            
            # Check for overlapping periods
            periods = Period.objects.all()
            for period in periods:
                period_start = datetime.strptime(period.start_time, '%H:%M')
                period_end = datetime.strptime(period.end_time, '%H:%M')
                
                # Check if the new period overlaps with an existing period
                if (start_datetime < period_end and end_datetime > period_start):
                    raise ValueError(f"This period overlaps with existing period '{period.name}'")
            
            # Create the period
            with transaction.atomic():
                period = Period(
                    name=name,
                    start_time=start_time,
                    end_time=end_time
                )
                period.save()
                
                messages.success(request, f"Period '{name}' created successfully!")
                return redirect('view_periods')
                
        except ValueError as e:
            messages.error(request, str(e))
            
    # For GET request or if there was an error in POST
    return render(request, 'schedule/periods/create_period.html')


def edit_period(request, period_id):
    """Edit an existing period."""
    period = get_object_or_404(Period, pk=period_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        try:
            # Validate input
            if not name:
                raise ValueError("Period name is required")
            
            if not start_time:
                raise ValueError("Start time is required")
            
            if not end_time:
                raise ValueError("End time is required")
            
            # Validate that start_time comes before end_time
            from datetime import datetime
            
            try:
                start_datetime = datetime.strptime(start_time, '%H:%M')
                end_datetime = datetime.strptime(end_time, '%H:%M')
                
                if start_datetime >= end_datetime:
                    raise ValueError("End time must be after start time")
            except ValueError as e:
                if "unconverted data remains" in str(e) or "does not match format" in str(e):
                    raise ValueError("Time must be in 24-hour format (HH:MM)")
                else:
                    raise
            
            # Check for overlapping periods, excluding this period
            periods = Period.objects.exclude(pk=period_id)
            for p in periods:
                p_start = datetime.strptime(p.start_time, '%H:%M')
                p_end = datetime.strptime(p.end_time, '%H:%M')
                
                # Check if the edited period overlaps with an existing period
                if (start_datetime < p_end and end_datetime > p_start):
                    raise ValueError(f"This period overlaps with existing period '{p.name}'")
            
            # Update the period
            with transaction.atomic():
                period.name = name
                period.start_time = start_time
                period.end_time = end_time
                period.save()
                
                messages.success(request, f"Period '{name}' updated successfully!")
                return redirect('view_periods')
                
        except ValueError as e:
            messages.error(request, str(e))
    
    # For GET request or if there was an error in POST
    return render(request, 'schedule/periods/edit_period.html', {'period': period})


def delete_period(request, period_id):
    """Delete a period."""
    period = get_object_or_404(Period, pk=period_id)
    
    if request.method == 'POST':
        # Check if there are any sections using this period
        if period.section_set.exists():
            messages.error(request, f"Cannot delete period '{period.name}' because it has sections assigned to it.")
            return redirect('view_periods')
        
        period_name = period.name
        period.delete()
        messages.success(request, f"Period '{period_name}' deleted successfully!")
        return redirect('view_periods')
    
    return render(request, 'schedule/periods/confirm_delete.html', {'period': period}) 