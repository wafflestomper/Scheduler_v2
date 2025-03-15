"""
Main views module that imports and exposes all views from modularized view files.
"""

# Import views from modular view files
from .views.main_views import index
from .views.student_views import (
    view_students, student_detail, edit_student, delete_student,
    export_student_schedules
)
from .views.course_views import (
    view_courses, create_course, edit_course, delete_course
)
from .views.teacher_views import (
    view_teachers, create_teacher, edit_teacher, delete_teacher
)
from .views.room_views import (
    view_rooms, create_room, edit_room, delete_room
)
from .views.period_views import (
    view_periods, create_period, edit_period, delete_period
)
from .views.section_views import (
    edit_section, get_conflicts, export_master_schedule,
    master_schedule, student_schedules, find_schedule_conflicts
)
from .views.schedule_generation_views import (
    schedule_generation, admin_reports, generate_schedules,
    create_core_sections, assign_students_to_core_sections,
    create_elective_sections, assign_students_to_elective_sections
)
from .views.import_export_views import (
    CSVUploadView, download_template_csv
)

# Export all views
__all__ = [
    # Main views
    'index',
    
    # Student views
    'view_students', 'student_detail', 'edit_student', 'delete_student',
    'export_student_schedules',
    
    # Course views
    'view_courses', 'create_course', 'edit_course', 'delete_course',
    
    # Teacher views
    'view_teachers', 'create_teacher', 'edit_teacher', 'delete_teacher',
    
    # Room views
    'view_rooms', 'create_room', 'edit_room', 'delete_room',
    
    # Period views
    'view_periods', 'create_period', 'edit_period', 'delete_period',
    
    # Section views
    'edit_section', 'get_conflicts', 'export_master_schedule',
    'master_schedule', 'student_schedules', 'find_schedule_conflicts',
    
    # Schedule generation views
    'schedule_generation', 'admin_reports', 'generate_schedules',
    'create_core_sections', 'assign_students_to_core_sections',
    'create_elective_sections', 'assign_students_to_elective_sections',
    
    # Import/export views
    'CSVUploadView', 'download_template_csv',
]
