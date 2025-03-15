#!/usr/bin/env python
import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

from schedule.models import Student, Course, Section, Period, TrimesterCourseGroup, Enrollment, CourseEnrollment
from django.db.models import Count, Q
import csv

def analyze_section_assignments():
    """Analyze current section assignments and identify issues."""
    print("Analyzing section assignments...")
    
    # Get all sections with enrollment counts
    sections = Section.objects.annotate(
        enrollment_count=Count('enrollment')
    ).order_by('course__id', 'section_number')
    
    # Count empty sections by course type
    empty_sections = sections.filter(enrollment_count=0)
    total_empty = empty_sections.count()
    
    # Get language course sections
    language_sections = empty_sections.filter(course__type='language')
    language_empty_count = language_sections.count()
    
    # Get trimester course sections
    trimester_course_ids = []
    for group in TrimesterCourseGroup.objects.all():
        trimester_course_ids.extend(list(group.courses.values_list('id', flat=True)))
    
    trimester_sections = empty_sections.filter(course__id__in=trimester_course_ids)
    trimester_empty_count = trimester_sections.count()
    
    # Get regular sections (not language or trimester)
    regular_sections = empty_sections.exclude(
        Q(course__type='language') | Q(course__id__in=trimester_course_ids)
    )
    regular_empty_count = regular_sections.count()
    
    # Print summary
    print("\n=== EMPTY SECTION SUMMARY ===")
    print(f"Total empty sections: {total_empty} out of {sections.count()} total sections")
    print(f"Empty language course sections: {language_empty_count}")
    print(f"Empty trimester course sections: {trimester_empty_count}")
    print(f"Empty regular course sections: {regular_empty_count}")
    
    # Check if students are enrolled in courses with empty sections
    empty_courses = Course.objects.filter(sections__in=empty_sections).distinct()
    print(f"\nCourses with empty sections: {empty_courses.count()}")
    
    for course in empty_courses:
        enrollment_count = CourseEnrollment.objects.filter(course=course).count()
        empty_section_count = empty_sections.filter(course=course).count()
        total_section_count = sections.filter(course=course).count()
        
        if enrollment_count > 0:
            print(f"Course {course.id} - {course.name}: {enrollment_count} student enrollments, "
                  f"{empty_section_count}/{total_section_count} empty sections")
    
    # Create detailed CSV report
    with open('section_analysis.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Course ID', 'Course Name', 'Type', 'Section ID', 'Period', 
                         'When', 'Students Enrolled', 'Students in Course', 'Status'])
        
        for section in sections:
            # Get enrollments for this section
            enrolled_count = section.enrollment_count
            
            # Get total enrollments in the course
            course_enrollment_count = CourseEnrollment.objects.filter(
                course=section.course
            ).count()
            
            # Determine if this is a trimester course
            is_trimester = section.course.id in trimester_course_ids
            
            # Determine course type for display
            if section.course.type == 'language':
                display_type = 'Language'
            elif is_trimester:
                display_type = 'Trimester'
            else:
                display_type = 'Regular'
            
            # Determine status
            if enrolled_count == 0 and course_enrollment_count > 0:
                status = 'EMPTY_WITH_ENROLLMENTS'
            elif enrolled_count == 0:
                status = 'EMPTY_NO_ENROLLMENTS'
            else:
                status = 'HAS_STUDENTS'
            
            writer.writerow([
                section.course.id,
                section.course.name,
                display_type,
                section.id,
                section.period.id if section.period else 'None',
                section.when if section.when else 'None',
                enrolled_count,
                course_enrollment_count,
                status
            ])
    
    print(f"\nDetailed report saved to section_analysis.csv")

if __name__ == "__main__":
    analyze_section_assignments() 