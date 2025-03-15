#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

from schedule.models import Course, TrimesterCourseGroup

def initialize_trimester_course_groups():
    """
    Initialize the trimester course groups for 6th grade:
    - Group 1: WH6 and HW6 (World History pair)
    - Group 2: CTA6 and TAC6 (Computer/Technology pair)
    - Group 3: WW6, Art6, Mus6 (Arts elective options)
    """
    print("Initializing 6th grade trimester course groups...")
    
    # Create courses if they don't exist
    courses_data = [
        {'id': 'WH6', 'name': 'World History 6', 'type': 'required_elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'HW6', 'name': 'History of the World 6', 'type': 'required_elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'CTA6', 'name': 'Computer Technology Applications 6', 'type': 'required_elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'TAC6', 'name': 'Technology and Computers 6', 'type': 'required_elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'WW6', 'name': 'Writers Workshop 6', 'type': 'elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'Art6', 'name': 'Art 6', 'type': 'elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'Mus6', 'name': 'Music 6', 'type': 'elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
    ]
    
    created_courses = {}
    for course_data in courses_data:
        course, created = Course.objects.get_or_create(
            id=course_data['id'],
            defaults={
                'name': course_data['name'],
                'type': course_data['type'],
                'grade_level': course_data['grade_level'],
                'max_students': course_data['max_students'],
                'duration': course_data['duration'],
            }
        )
        created_courses[course_data['id']] = course
        if created:
            print(f"Created course: {course.name}")
        else:
            print(f"Course already exists: {course.name}")
    
    # Create the trimester course groups
    groups_data = [
        {
            'name': 'World History Group',
            'description': 'Required pair of 6th grade world history courses',
            'group_type': 'required_pair',
            'courses': ['WH6', 'HW6']
        },
        {
            'name': 'Computer Technology Group',
            'description': 'Required pair of 6th grade computer technology courses',
            'group_type': 'required_pair',
            'courses': ['CTA6', 'TAC6']
        },
        {
            'name': 'Arts Electives Group',
            'description': 'Elective options for 6th grade arts courses',
            'group_type': 'elective',
            'courses': ['WW6', 'Art6', 'Mus6']
        }
    ]
    
    for group_data in groups_data:
        group, created = TrimesterCourseGroup.objects.get_or_create(
            name=group_data['name'],
            defaults={
                'description': group_data['description'],
                'group_type': group_data['group_type'],
            }
        )
        
        # Add courses to the group
        for course_id in group_data['courses']:
            group.courses.add(created_courses[course_id])
        
        if created:
            print(f"Created group: {group.name} with {group.courses.count()} courses")
        else:
            print(f"Group already exists: {group.name}")
    
    print("Initialization complete!")

if __name__ == "__main__":
    initialize_trimester_course_groups() 