"""
Views for the section settings administration interface.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse

from ..models import SectionSettings
from ..forms import SectionSettingsForm


def section_settings(request):
    """
    View and edit section settings.
    """
    # Get the first settings object or create default if none exists
    settings = SectionSettings.objects.first()
    if not settings:
        settings = SectionSettings.objects.create(
            name="Default Settings",
            core_min_size=15,
            elective_min_size=10,
            required_elective_min_size=12,
            language_min_size=12,
            default_max_size=30,
            enforce_min_sizes=True,
            auto_cancel_below_min=False
        )
    
    if request.method == 'POST':
        form = SectionSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated successfully!")
            return redirect('section_settings')
    else:
        form = SectionSettingsForm(instance=settings)
    
    context = {
        'form': form,
        'settings': settings,
    }
    return render(request, 'schedule/section_settings.html', context) 