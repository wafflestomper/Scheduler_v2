#!/usr/bin/env python
import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

from schedule.models import Student, Course, Section, Period, TrimesterCourseGroup, Enrollment, CourseEnrollment
from schedule.utils.trimester_course_utils import assign_trimester_courses, get_trimester_course_conflicts
from django.db import transaction

def run_tests():
    """Run tests to verify the trimester course functionality works correctly."""
    print("Starting trimester course tests...")
    
    # Clean up any data from previous test runs
    cleanup_test_data()
    
    # Create test data
    setup_test_data()
    
    # Run the tests
    test_trimester_course_group_model()
    test_assign_trimester_courses()
    test_get_trimester_course_conflicts()
    
    # Clean up after tests
    cleanup_test_data()
    
    print("\nAll tests completed!")

def setup_test_data():
    """Set up test data for the tests."""
    print("\nSetting up test data...")
    
    # Create test courses
    courses = [
        {'id': 'WH6_TEST', 'name': 'Test World History 6', 'type': 'required_elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'HW6_TEST', 'name': 'Test History of the World 6', 'type': 'required_elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'CTA6_TEST', 'name': 'Test Computer Tech 6', 'type': 'required_elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'TAC6_TEST', 'name': 'Test Tech and Comp 6', 'type': 'required_elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'WW6_TEST', 'name': 'Test Writers Workshop 6', 'type': 'elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'ART6_TEST', 'name': 'Test Art 6', 'type': 'elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
        {'id': 'MUS6_TEST', 'name': 'Test Music 6', 'type': 'elective', 'grade_level': 6, 'max_students': 25, 'duration': 'trimester'},
    ]
    
    for course_data in courses:
        Course.objects.get_or_create(
            id=course_data['id'],
            defaults={
                'name': course_data['name'],
                'type': course_data['type'],
                'grade_level': course_data['grade_level'],
                'max_students': course_data['max_students'],
                'duration': course_data['duration'],
                'eligible_teachers': 'T001|T002',  # Dummy teacher IDs
            }
        )
    
    # Create test period
    period, _ = Period.objects.get_or_create(
        id='P1_TEST',
        defaults={
            'period_name': 'Test Period 1',
            'days': 'M|T|W|TH|F',
            'slot': '1',
            'start_time': '08:00',
            'end_time': '08:50',
        }
    )
    
    # Create test sections for each course in each trimester
    for course_id in ['WH6_TEST', 'HW6_TEST', 'CTA6_TEST', 'TAC6_TEST', 'WW6_TEST', 'ART6_TEST', 'MUS6_TEST']:
        course = Course.objects.get(id=course_id)
        
        for trimester in ['t1', 't2', 't3']:
            section_id = f"{course_id}_{trimester}_TEST"
            Section.objects.get_or_create(
                id=section_id,
                defaults={
                    'course': course,
                    'section_number': 1,
                    'period': period,
                    'when': trimester,
                }
            )
    
    # Create test trimester course groups
    groups_data = [
        {
            'name': 'Test World History Group',
            'description': 'Test history group',
            'group_type': 'required_pair',
            'courses': ['WH6_TEST', 'HW6_TEST']
        },
        {
            'name': 'Test Computer Tech Group',
            'description': 'Test computer group',
            'group_type': 'required_pair',
            'courses': ['CTA6_TEST', 'TAC6_TEST']
        },
        {
            'name': 'Test Arts Electives Group',  # Changed to match the exact name in error message
            'description': 'Test arts electives group',
            'group_type': 'elective',
            'courses': ['WW6_TEST', 'ART6_TEST', 'MUS6_TEST']
        }
    ]
    
    for group_data in groups_data:
        group, _ = TrimesterCourseGroup.objects.get_or_create(
            name=group_data['name'],
            defaults={
                'description': group_data['description'],
                'group_type': group_data['group_type'],
            }
        )
        
        # Add courses to the group
        for course_id in group_data['courses']:
            course = Course.objects.get(id=course_id)
            group.courses.add(course)
    
    # Create test student
    student, _ = Student.objects.get_or_create(
        id='S001_TEST',
        defaults={
            'name': 'Test Student',
            'grade_level': 6,
        }
    )
    
    # Enroll student in one course from each group
    course_enrollments = [
        {'student_id': 'S001_TEST', 'course_id': 'WH6_TEST'},
        {'student_id': 'S001_TEST', 'course_id': 'CTA6_TEST'},
        {'student_id': 'S001_TEST', 'course_id': 'ART6_TEST'}  # Changed from WW6_TEST to ART6_TEST for clarity
    ]
    
    for enrollment_data in course_enrollments:
        CourseEnrollment.objects.get_or_create(
            student_id=enrollment_data['student_id'],
            course_id=enrollment_data['course_id']
        )
    
    print("Test data setup complete!")

def cleanup_test_data():
    """Clean up test data from the database."""
    print("\nCleaning up test data...")
    
    # Use atomic transaction to ensure all data is cleaned up together
    with transaction.atomic():
        # Delete test enrollments
        Enrollment.objects.filter(student__id='S001_TEST').delete()
        CourseEnrollment.objects.filter(student__id='S001_TEST').delete()
        
        # Delete test student
        Student.objects.filter(id='S001_TEST').delete()
        
        # Delete test sections
        Section.objects.filter(id__endswith='_TEST').delete()
        
        # Delete test period
        Period.objects.filter(id='P1_TEST').delete()
        
        # Delete test courses
        Course.objects.filter(id__endswith='_TEST').delete()
        
        # Delete test trimester course groups
        TrimesterCourseGroup.objects.filter(name__startswith='Test ').delete()
    
    print("Test data cleanup complete!")

def test_trimester_course_group_model():
    """Test the TrimesterCourseGroup model."""
    print("\nTesting TrimesterCourseGroup model...")
    
    # Check that we have our test groups
    groups = TrimesterCourseGroup.objects.filter(name__startswith='Test ')
    assert groups.count() == 3, f"Expected 3 test groups, found {groups.count()}"
    
    # Check that each group has the correct number of courses
    history_group = TrimesterCourseGroup.objects.get(name='Test World History Group')
    assert history_group.courses.count() == 2, f"Expected 2 courses in history group, found {history_group.courses.count()}"
    
    tech_group = TrimesterCourseGroup.objects.get(name='Test Computer Tech Group')
    assert tech_group.courses.count() == 2, f"Expected 2 courses in tech group, found {tech_group.courses.count()}"
    
    arts_group = TrimesterCourseGroup.objects.get(name='Test Arts Electives Group')
    assert arts_group.courses.count() == 3, f"Expected 3 courses in arts group, found {arts_group.courses.count()}"
    
    print("TrimesterCourseGroup model test passed!")

def test_assign_trimester_courses():
    """Test the assign_trimester_courses function."""
    print("\nTesting assign_trimester_courses function...")
    
    student = Student.objects.get(id='S001_TEST')
    
    # Debugging: Check all trimester course groups
    print("\nAll trimester course groups:")
    all_groups = []
    for group in TrimesterCourseGroup.objects.all():
        print(f"Group: {group.name}, ID: {group.id}, Type: {group.group_type}")
        print(f"  Courses: {', '.join([c.id for c in group.courses.all()])}")
        if group.name.startswith('Test '):
            all_groups.append(group.id)
    
    # Debugging: Check student enrollments
    print("\nStudent enrollments:")
    for enrollment in CourseEnrollment.objects.filter(student=student):
        print(f"Enrolled in: {enrollment.course.id} - {enrollment.course.name}")
    
    # Check that the student is enrolled in test courses
    enrollments = CourseEnrollment.objects.filter(student=student)
    assert enrollments.count() == 3, f"Expected 3 course enrollments, found {enrollments.count()}"
    
    # Run the assignment function with explicit group IDs
    print(f"\nUsing test group IDs: {all_groups}")
    success, message, assignments = assign_trimester_courses(student, group_ids=all_groups)
    
    # Debugging: Print the message regardless of success
    print(f"\nAssignment result: {success}, Message: {message}")
    
    # Check that the assignment was successful
    assert success, f"Assignment failed with message: {message}"
    assert len(assignments) == 3, f"Expected 3 assignments, found {len(assignments)}"
    
    # Check that each assignment is for a different trimester
    trimesters = [enrollment.section.when for enrollment in assignments]
    assert len(set(trimesters)) == 3, f"Expected 3 different trimesters, found {len(set(trimesters))}"
    
    # Check that all assignments are for the same period
    periods = [enrollment.section.period_id for enrollment in assignments]
    assert len(set(periods)) == 1, f"Expected 1 period, found {len(set(periods))}"
    
    print("assign_trimester_courses function test passed!")

def test_get_trimester_course_conflicts():
    """Test the get_trimester_course_conflicts function."""
    print("\nTesting get_trimester_course_conflicts function...")
    
    student = Student.objects.get(id='S001_TEST')
    
    # Get test group IDs
    test_group_ids = []
    for group in TrimesterCourseGroup.objects.filter(name__startswith='Test '):
        test_group_ids.append(group.id)
    
    print(f"\nUsing test group IDs: {test_group_ids}")
    
    # First verify no conflicts with proper assignments
    conflicts = get_trimester_course_conflicts(student, group_ids=test_group_ids)
    assert len(conflicts) == 0, f"Expected 0 conflicts, found {len(conflicts)}: {conflicts}"
    
    # Now create a conflict by assigning two courses to the same trimester
    # First, clear existing enrollments
    Enrollment.objects.filter(student=student).delete()
    
    # Create conflicting enrollments
    section1 = Section.objects.get(id='WH6_TEST_t1_TEST')
    section2 = Section.objects.get(id='CTA6_TEST_t1_TEST')  # Same trimester as section1
    section3 = Section.objects.get(id='ART6_TEST_t3_TEST')
    
    Enrollment.objects.create(student=student, section=section1)
    Enrollment.objects.create(student=student, section=section2)
    Enrollment.objects.create(student=student, section=section3)
    
    # Check for conflicts
    conflicts = get_trimester_course_conflicts(student, group_ids=test_group_ids)
    assert len(conflicts) > 0, f"Expected at least 1 conflict, found {len(conflicts)}"
    print(f"Detected conflicts: {conflicts}")
    
    print("get_trimester_course_conflicts function test passed!")

if __name__ == "__main__":
    run_tests() 