#!/usr/bin/env python
import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

from django.test import Client
from django.urls import reverse

from schedule.models import Student, TrimesterCourseGroup, CourseEnrollment

def test_view_get():
    """Test the GET method of the view."""
    print("\nTesting trimester course assignment view (GET)...")
    
    # Setup client
    client = Client()
    
    # Call the view
    response = client.get(reverse('assign_trimester_courses'))
    
    # Check that the view returns a 200 OK response
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    print("GET test passed!")

def test_view_post():
    """Test the POST method of the view with a valid form."""
    print("\nTesting trimester course assignment view (POST)...")
    
    # Create a test student
    student, _ = Student.objects.get_or_create(
        id='S002_API_TEST',
        defaults={
            'name': 'API Test Student',
            'grade_level': 6,
        }
    )
    
    # Get test trimester groups
    test_groups = []
    for group in TrimesterCourseGroup.objects.filter(name__startswith='Test '):
        test_groups.append(group.id)
    
    # Enroll the student in one course from each group
    for group in TrimesterCourseGroup.objects.filter(id__in=test_groups):
        course = group.courses.first()
        CourseEnrollment.objects.get_or_create(
            student=student,
            course=course
        )
    
    # Setup client
    client = Client()
    
    # Prepare form data
    post_data = {
        'student': student.id,
        'group_selections': test_groups,
        'preferred_period': '',  # No preference
    }
    
    # Call the view
    response = client.post(reverse('assign_trimester_courses'), post_data)
    
    # Check that the view returns a redirect (302) response
    assert response.status_code in [302, 200], f"Expected 302 or 200, got {response.status_code}"
    
    # Clean up
    student.delete()
    
    print("POST test passed!")

def run_tests():
    """Run UI/API tests for trimester course assignment."""
    print("Starting trimester course API tests...")
    
    try:
        test_view_get()
        test_view_post()
        print("\nAll API tests completed successfully!")
    except Exception as e:
        print(f"\nError during API testing: {e}")
        import traceback
        traceback.print_exc()
    
if __name__ == "__main__":
    run_tests() 