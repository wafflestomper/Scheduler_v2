from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.CSVUploadView.as_view(), name='csv_upload'),
    path('generate/', views.schedule_generation, name='schedule_generation'),
    path('master/', views.master_schedule, name='master_schedule'),
    path('students/', views.student_schedules, name='student_schedules'),
    path('edit-section/<int:section_id>/', views.edit_section, name='edit_section'),
    path('conflicts/', views.get_conflicts, name='get_conflicts'),
    path('export/students/', views.export_student_schedules, name='export_student_schedules'),
    path('export/master/', views.export_master_schedule, name='export_master_schedule'),
] 