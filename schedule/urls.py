from django.urls import path
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
    master_schedule, student_schedules
)
from .views.schedule_generation_views import (
    schedule_generation, admin_reports
)
from .views.import_export_views import (
    CSVUploadView, download_template_csv
)
from .views.enrollment_views import (
    enroll_students, enroll_student_to_course, batch_enroll_students, assign_students_to_sections
)

urlpatterns = [
    path('', index, name='index'),
    path('upload/', CSVUploadView.as_view(), name='csv_upload'),
    path('generate/', schedule_generation, name='schedule_generation'),
    path('master/', master_schedule, name='master_schedule'),
    path('students/', student_schedules, name='student_schedules'),
    path('edit-section/<int:section_id>/', edit_section, name='edit_section'),
    path('conflicts/', get_conflicts, name='get_conflicts'),
    path('export/students/', export_student_schedules, name='export_student_schedules'),
    path('export/master/', export_master_schedule, name='export_master_schedule'),
    path('download-template/<str:template_type>/', download_template_csv, name='download_template'),
    path('view-students/', view_students, name='view_students'),
    path('student/<str:student_id>/', student_detail, name='student_detail'),
    path('student/<str:student_id>/edit/', edit_student, name='edit_student'),
    path('student/<str:student_id>/delete/', delete_student, name='delete_student'),
    path('reports/', admin_reports, name='admin_reports'),
    path('periods/', view_periods, name='view_periods'),
    path('periods/create/', create_period, name='create_period'),
    path('periods/<str:period_id>/edit/', edit_period, name='edit_period'),
    path('periods/<str:period_id>/delete/', delete_period, name='delete_period'),
    path('teachers/', view_teachers, name='view_teachers'),
    path('teachers/create/', create_teacher, name='create_teacher'),
    path('teachers/<str:teacher_id>/edit/', edit_teacher, name='edit_teacher'),
    path('teachers/<str:teacher_id>/delete/', delete_teacher, name='delete_teacher'),
    path('rooms/', view_rooms, name='view_rooms'),
    path('rooms/create/', create_room, name='create_room'),
    path('rooms/<str:room_id>/edit/', edit_room, name='edit_room'),
    path('rooms/<str:room_id>/delete/', delete_room, name='delete_room'),
    path('courses/', view_courses, name='view_courses'),
    path('courses/create/', create_course, name='create_course'),
    path('courses/<str:course_id>/edit/', edit_course, name='edit_course'),
    path('courses/<str:course_id>/delete/', delete_course, name='delete_course'),
    
    # Enrollment management
    path('enroll-students/', enroll_students, name='enroll_students'),
    path('api/enroll-student-to-course/', enroll_student_to_course, name='enroll_student_to_course'),
    path('api/batch-enroll-students/', batch_enroll_students, name='batch_enroll_students'),
    path('api/assign-students-to-sections/', assign_students_to_sections, name='assign_students_to_sections'),
] 