"""
Utility functions for working with sections and section settings.
"""
from django.db.models import Count, Q, F
from ..models import Section, SectionSettings


def get_section_min_size(section):
    """
    Get the minimum size for a section based on its course type.
    """
    # Get active settings
    settings = SectionSettings.objects.first()
    if not settings:
        # Default values if no settings exist
        return {
            'core': 15,
            'elective': 10,
            'required_elective': 12,
            'language': 12
        }.get(section.course.type, 10)
    
    return settings.get_min_size_for_course_type(section.course.type)


def get_sections_below_min_size():
    """
    Get all sections that are below their minimum size.
    Returns a list of tuples: (section, current_size, min_size)
    """
    sections = Section.objects.all().prefetch_related('students').select_related('course')
    
    # Get settings
    settings = SectionSettings.objects.first()
    if not settings or not settings.enforce_min_sizes:
        return []
    
    sections_below_min = []
    
    for section in sections:
        current_size = section.students.count()
        min_size = get_section_min_size(section)
        
        if current_size < min_size:
            sections_below_min.append((section, current_size, min_size))
    
    return sorted(sections_below_min, key=lambda x: (x[0].course.type, x[0].course.name, x[0].section_number))


def get_sections_stats():
    """
    Get statistics about section sizes.
    """
    settings = SectionSettings.objects.first()
    if not settings:
        return {}
    
    sections = Section.objects.all().prefetch_related('students').select_related('course')
    
    stats = {
        'total_sections': sections.count(),
        'sections_below_min': 0,
        'sections_at_or_above_min': 0,
        'by_course_type': {
            'core': {'total': 0, 'below_min': 0},
            'elective': {'total': 0, 'below_min': 0},
            'required_elective': {'total': 0, 'below_min': 0},
            'language': {'total': 0, 'below_min': 0},
        }
    }
    
    for section in sections:
        course_type = section.course.type
        if course_type not in stats['by_course_type']:
            stats['by_course_type'][course_type] = {'total': 0, 'below_min': 0}
        
        stats['by_course_type'][course_type]['total'] += 1
        
        current_size = section.students.count()
        min_size = get_section_min_size(section)
        
        if current_size < min_size:
            stats['sections_below_min'] += 1
            stats['by_course_type'][course_type]['below_min'] += 1
        else:
            stats['sections_at_or_above_min'] += 1
    
    return stats 