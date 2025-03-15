from django.contrib import admin
from .models import Teacher, Room, Student, Course, Period, Section

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
    list_display = ('id', 'name', 'grade_level')
    search_fields = ('id', 'name')
    list_filter = ('grade_level',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type', 'grade_level', 'max_students')
    search_fields = ('id', 'name')
    list_filter = ('type', 'grade_level')

@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ('id', 'day', 'slot', 'start_time', 'end_time')
    list_filter = ('day', 'slot')

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'teacher', 'room', 'period')
    search_fields = ('course__name', 'teacher__name', 'room__number')
    list_filter = ('course__type', 'teacher', 'room', 'period')
