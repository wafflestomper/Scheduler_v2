from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from ..models import Period
from django.db import transaction
from datetime import datetime, time


def view_periods(request):
    """View all periods."""
    periods = Period.objects.all().order_by('slot', 'start_time')
    return render(request, 'schedule/view_periods.html', {'periods': periods})


def create_period(request):
    """Create a new period."""
    if request.method == 'POST':
        period_name = request.POST.get('period_name', '')
        days = request.POST.get('days', 'M')
        slot = request.POST.get('slot')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        try:
            # Validate input
            if not slot:
                raise ValueError("Period slot is required")
            
            if not start_time:
                raise ValueError("Start time is required")
            
            if not end_time:
                raise ValueError("End time is required")
            
            # Validate that start_time comes before end_time
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
            
            # Create the period
            with transaction.atomic():
                # Generate a period ID based on the slot
                period_id = f"P{Period.objects.count() + 1:03d}"
                
                period = Period(
                    id=period_id,
                    period_name=period_name,
                    days=days,
                    slot=slot,
                    start_time=start_time,
                    end_time=end_time
                )
                period.save()
                
                display_name = period_name if period_name else f"Period {slot}"
                messages.success(request, f"{display_name} created successfully!")
                return redirect('view_periods')
                
        except ValueError as e:
            messages.error(request, str(e))
            
    # For GET request or if there was an error in POST
    return render(request, 'schedule/create_period.html', {
        'day_choices': Period.DAY_CHOICES
    })


def edit_period(request, period_id):
    """Edit an existing period."""
    period = get_object_or_404(Period, pk=period_id)
    
    if request.method == 'POST':
        period_name = request.POST.get('period_name', '')
        days = request.POST.get('days', 'M')
        slot = request.POST.get('slot')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        try:
            # Validate input
            if not slot:
                raise ValueError("Period slot is required")
            
            if not start_time:
                raise ValueError("Start time is required")
            
            if not end_time:
                raise ValueError("End time is required")
            
            # Validate that start_time comes before end_time
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
            
            # Update the period
            with transaction.atomic():
                period.period_name = period_name
                period.days = days
                period.slot = slot
                period.start_time = start_time
                period.end_time = end_time
                period.save()
                
                display_name = period_name if period_name else f"Period {slot}"
                messages.success(request, f"{display_name} updated successfully!")
                return redirect('view_periods')
                
        except ValueError as e:
            messages.error(request, str(e))
    
    # For GET request or if there was an error in POST
    return render(request, 'schedule/edit_period.html', {
        'period': period,
        'day_choices': Period.DAY_CHOICES
    })


def delete_period(request, period_id):
    """Delete a period."""
    period = get_object_or_404(Period, pk=period_id)
    
    if request.method == 'POST':
        # Check if there are any sections using this period
        from ..models import Section
        if Section.objects.filter(period=period).exists():
            messages.error(request, f"Cannot delete period '{period}' because it has sections assigned to it.")
            return redirect('view_periods')
        
        period_name = str(period)
        period.delete()
        messages.success(request, f"{period_name} deleted successfully!")
        return redirect('view_periods')
    
    return render(request, 'schedule/delete_period_confirm.html', {'period': period}) 