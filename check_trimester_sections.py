#!/usr/bin/env python
import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

from schedule.models import Student, Course, Section, Period, TrimesterCourseGroup, Enrollment, CourseEnrollment

def check_trimester_sections():
    """
    Check if sections for trimester courses are properly configured with periods.
    """
    print("Checking trimester course section configuration...")
    
    # Get all trimester course groups
    trimester_groups = TrimesterCourseGroup.objects.all().prefetch_related('courses')
    
    # Get all courses in these groups
    all_trimester_courses = []
    for group in trimester_groups:
        all_trimester_courses.extend(list(group.courses.all()))
    
    print(f"\nFound {len(all_trimester_courses)} trimester courses")
    
    # Check section configuration for each course
    for course in all_trimester_courses:
        sections = Section.objects.filter(course=course)
        sections_with_period = sections.exclude(period=None)
        sections_by_trimester = {}
        
        for section in sections:
            trimester = section.when
            if trimester not in sections_by_trimester:
                sections_by_trimester[trimester] = []
            sections_by_trimester[trimester].append(section)
        
        print(f"\nCourse: {course.id} - {course.name}")
        print(f"Total sections: {sections.count()}")
        print(f"Sections with periods: {sections_with_period.count()}")
        
        # Print details for each trimester
        for trimester, trimester_sections in sections_by_trimester.items():
            print(f"  Trimester {trimester}: {len(trimester_sections)} sections")
            for section in trimester_sections:
                period_info = section.period.id if section.period else "NO PERIOD"
                print(f"    Section {section.id}: Period {period_info}")
    
    # Check periods for consistency
    print("\nChecking for valid period combinations...")
    period_combinations = find_valid_period_combinations(all_trimester_courses)
    
    # Display results of period checks
    if period_combinations:
        print("\nFound the following valid period combinations:")
        for period_id, details in period_combinations.items():
            print(f"\nPeriod {period_id}:")
            print(f"  Courses with sections in all trimesters:")
            for course_id in details['complete_courses']:
                print(f"    - {course_id}")
            print(f"  Missing sections:")
            for course_id, missing in details['missing_sections'].items():
                print(f"    - {course_id}: missing in {', '.join(missing)}")
    else:
        print("\nNo valid period combinations found where each course has a section in each trimester.")

def find_valid_period_combinations(courses):
    """Find valid period combinations for trimester courses."""
    # Get all periods
    periods = Period.objects.all()
    
    # Check each period if it has sections for all courses in all trimesters
    valid_periods = {}
    
    for period in periods:
        period_data = {
            'complete_courses': [],
            'missing_sections': {},
        }
        
        for course in courses:
            # Check if this course has sections in all trimesters for this period
            missing_trimesters = []
            for trimester in ['t1', 't2', 't3']:
                has_section = Section.objects.filter(
                    course=course,
                    period=period,
                    when=trimester
                ).exists()
                
                if not has_section:
                    missing_trimesters.append(trimester)
            
            if not missing_trimesters:
                period_data['complete_courses'].append(course.id)
            else:
                period_data['missing_sections'][course.id] = missing_trimesters
        
        # Add this period to valid periods if at least one course is complete
        if period_data['complete_courses']:
            valid_periods[period.id] = period_data
    
    return valid_periods

if __name__ == "__main__":
    check_trimester_sections() 