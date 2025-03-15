#!/usr/bin/env python
import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

from schedule.models import Student, Course, Section, Period, TrimesterCourseGroup, CourseGroup, Enrollment, CourseEnrollment
from schedule.utils.balance_assignment import unified_assignment
import json

def run_test():
    """Test the unified assignment algorithm."""
    print("Testing unified assignment algorithm...")
    
    # Run the unified assignment algorithm
    results = unified_assignment()
    
    # Print the results in a readable format
    print("\nAssignment Results:")
    print(f"Total Assignments: {results['initial_assignments']}")
    print(f"Total Failures: {results['initial_failures']}")
    print(f"Conflicts Resolved: {results['conflicts_resolved']}")
    print(f"Unresolvable Conflicts: {results['unresolvable_conflicts']}")
    
    # Special course type results
    print("\nSpecial Course Results:")
    print(f"Language Course Assignments: {results['language_assignments']}")
    print(f"Language Course Failures: {results['language_failures']}")
    print(f"Trimester Course Assignments: {results['trimester_assignments']}")
    print(f"Trimester Course Failures: {results['trimester_failures']}")
    print(f"Regular Course Assignments: {results['regular_assignments']}")
    print(f"Regular Course Failures: {results['regular_failures']}")
    
    # Print any errors
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"- {error}")
    
    # Count assignments by course type
    language_enrollments = Enrollment.objects.filter(
        section__course__type='language'
    ).count()
    
    # Get all trimester courses
    trimester_courses = []
    for group in TrimesterCourseGroup.objects.all():
        trimester_courses.extend(list(group.courses.values_list('id', flat=True)))
    
    trimester_enrollments = Enrollment.objects.filter(
        section__course__id__in=trimester_courses
    ).count()
    
    # Verification summary
    print("\nVerification Summary:")
    print(f"Language Course Enrollments in Database: {language_enrollments}")
    print(f"Trimester Course Enrollments in Database: {trimester_enrollments}")
    print(f"Total Special Course Enrollments: {language_enrollments + trimester_enrollments}")

if __name__ == "__main__":
    run_test() 