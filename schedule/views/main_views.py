from django.shortcuts import render
from ..models import Teacher, Room, Student, Course, Period, Section, SectionSettings
from django.db.models import Q


def index(request):
    """Main index page."""
    # Ensure we have at least one settings object
    _ensure_default_settings()
    
    context = {
        'num_students': Student.objects.count(),
        'num_teachers': Teacher.objects.count(),
        'num_rooms': Room.objects.count(),
        'num_courses': Course.objects.count(),
        'num_sections': Section.objects.count(),
    }
    return render(request, 'schedule/index.html', context)


def _ensure_default_settings():
    """
    Ensure that we have at least one default settings object.
    This is called when the app is first loaded to ensure there's always
    a valid settings object available.
    """
    if not SectionSettings.objects.exists():
        SectionSettings.objects.create(
            name="Default Settings",
            core_min_size=15,
            elective_min_size=10,
            required_elective_min_size=12,
            language_min_size=12,
            default_max_size=30,
            enforce_min_sizes=True,
            auto_cancel_below_min=False
        ) 