#!/usr/bin/env python
import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

from schedule.models import TrimesterCourseGroup, CourseEnrollment

def inspect_trimester_groups():
    """Inspect trimester course groups and enrollments."""
    print("Inspecting trimester course groups...")
    
    # Get all trimester course groups
    groups = TrimesterCourseGroup.objects.all().prefetch_related('courses')
    
    print(f"\nFound {groups.count()} trimester course groups:")
    
    for group in groups:
        courses = list(group.courses.all())
        course_ids = [c.id for c in courses]
        
        print(f"\nGroup: {group.name}")
        print(f"Type: {group.group_type}")
        print(f"Courses: {course_ids}")
        
        # Check enrollments for each course
        for course in courses:
            enrollments = CourseEnrollment.objects.filter(course=course)
            print(f"  {course.id}: {enrollments.count()} student enrollments")
            
            # Show sample of enrolled students
            if enrollments.exists():
                sample_students = enrollments[:3]
                student_names = [e.student.name for e in sample_students]
                print(f"    Sample students: {', '.join(student_names)}")

if __name__ == "__main__":
    inspect_trimester_groups() 