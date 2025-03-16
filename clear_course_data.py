#!/usr/bin/env python

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scheduler.settings')
django.setup()

from schedule.models import (
    Course, 
    Section, 
    Enrollment, 
    CourseEnrollment, 
    CourseGroup, 
    TrimesterCourseGroup
)

def clear_course_data():
    print("Deleting all course-related data...")
    
    # First delete related models
    print(f"Deleting {Enrollment.objects.count()} enrollments...")
    Enrollment.objects.all().delete()
    
    print(f"Deleting {CourseEnrollment.objects.count()} course enrollments...")
    CourseEnrollment.objects.all().delete()
    
    print(f"Deleting {Section.objects.count()} sections...")
    Section.objects.all().delete()
    
    # Remove course relationships
    print("Clearing course groups...")
    for group in CourseGroup.objects.all():
        group.courses.clear()
    
    print("Clearing trimester course groups...")
    for group in TrimesterCourseGroup.objects.all():
        group.courses.clear()
    
    # Delete course groups
    print(f"Deleting {CourseGroup.objects.count()} course groups...")
    CourseGroup.objects.all().delete()
    
    print(f"Deleting {TrimesterCourseGroup.objects.count()} trimester course groups...")
    TrimesterCourseGroup.objects.all().delete()
    
    # Finally delete courses
    print(f"Deleting {Course.objects.count()} courses...")
    Course.objects.all().delete()
    
    print("All course and section data has been cleared!")

if __name__ == "__main__":
    clear_course_data() 