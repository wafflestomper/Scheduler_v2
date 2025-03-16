from django.contrib import admin
from .models import (
    Teacher, Room, Student, Course, Period, 
    Section, Enrollment, CourseEnrollment, CourseGroup,
    TrimesterCourseGroup, SectionSettings
)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'subjects')
    search_fields = ('id', 'name', 'subjects')
    list_filter = ('subjects',)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'number', 'type', 'capacity')
    search_fields = ('id', 'number')
    list_filter = ('type',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'grade_level', 'preferences')
    search_fields = ('id', 'name', 'preferences')
    list_filter = ('grade_level',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type', 'grade_level', 'max_students', 'duration')
    search_fields = ('id', 'name')
    list_filter = ('type', 'grade_level', 'duration')

@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ('id', 'period_name', 'days', 'slot', 'start_time', 'end_time')
    search_fields = ('id', 'period_name', 'days', 'slot')

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'section_number', 'teacher', 'period', 'room', 'when')
    search_fields = ('id', 'course__name', 'teacher__name', 'room__number')
    list_filter = ('when',)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'section', 'date_enrolled')
    search_fields = ('student__name', 'section__course__name')
    list_filter = ('date_enrolled',)

@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'date_enrolled')
    search_fields = ('student__name', 'course__name')
    list_filter = ('date_enrolled',)

@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'preferred_period', 'get_courses_count')
    search_fields = ('name', 'description')
    filter_horizontal = ('courses',)

@admin.register(TrimesterCourseGroup)
class TrimesterCourseGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'group_type', 'description', 'preferred_period', 'get_courses_count')
    list_filter = ('group_type',)
    search_fields = ('name', 'description')
    filter_horizontal = ('courses',)

@admin.register(SectionSettings)
class SectionSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'core_min_size', 'elective_min_size', 'required_elective_min_size', 
                   'language_min_size', 'default_max_size', 'enforce_min_sizes', 'auto_cancel_below_min',
                   'updated_at')
    fieldsets = (
        ('General', {
            'fields': ('name', 'enforce_min_sizes', 'auto_cancel_below_min')
        }),
        ('Minimum Sizes by Course Type', {
            'fields': ('core_min_size', 'elective_min_size', 'required_elective_min_size', 'language_min_size')
        }),
        ('Default Maximum Size', {
            'fields': ('default_max_size',)
        }),
    )
