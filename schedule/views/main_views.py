from django.shortcuts import render
from ..models import Teacher, Room, Student, Course, Period, Section


def index(request):
    """Main index page."""
    context = {
        'num_students': Student.objects.count(),
        'num_teachers': Teacher.objects.count(),
        'num_rooms': Room.objects.count(),
        'num_courses': Course.objects.count(),
        'num_sections': Section.objects.count(),
    }
    return render(request, 'schedule/index.html', context) 