#!/usr/bin/env python
import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

from schedule.models import TrimesterCourseGroup, Course
from schedule.utils.trimester_course_utils import assign_trimester_courses, get_trimester_course_conflicts

def verify_implementation():
    """
    Verify that the trimester course system is correctly implemented by checking the database.
    """
    print("Verifying trimester course system implementation...")
    
    # Check TrimesterCourseGroup model
    verify_model()
    
    # Check utility functions
    verify_utils()
    
    print("\nVerification complete! The trimester course system is correctly implemented.")

def verify_model():
    """Verify the TrimesterCourseGroup model."""
    print("\nVerifying TrimesterCourseGroup model...")
    
    # Check if the model exists and has data
    group_count = TrimesterCourseGroup.objects.count()
    print(f"Found {group_count} trimester course groups")
    assert group_count > 0, "No trimester course groups found in the database"
    
    # Check the structure of a group
    group = TrimesterCourseGroup.objects.first()
    print(f"Example group: {group.name} ({group.get_group_type_display()})")
    print(f"  Description: {group.description}")
    print(f"  Courses: {', '.join([c.id for c in group.courses.all()])}")
    
    # Check that the group has the correct attributes
    assert hasattr(group, 'name'), "TrimesterCourseGroup model missing 'name' attribute"
    assert hasattr(group, 'group_type'), "TrimesterCourseGroup model missing 'group_type' attribute"
    assert hasattr(group, 'courses'), "TrimesterCourseGroup model missing 'courses' relationship"
    
    print("TrimesterCourseGroup model verification passed!")

def verify_utils():
    """Verify the utility functions for trimester course assignment."""
    print("\nVerifying trimester course utility functions...")
    
    # Check that the utility functions exist
    import inspect
    from schedule.utils import trimester_course_utils
    
    assert hasattr(trimester_course_utils, 'assign_trimester_courses'), "Missing assign_trimester_courses function"
    assert hasattr(trimester_course_utils, 'get_trimester_course_conflicts'), "Missing get_trimester_course_conflicts function"
    assert hasattr(trimester_course_utils, 'balance_trimester_course_sections'), "Missing balance_trimester_course_sections function"
    
    # Check function signatures
    assign_sig = inspect.signature(trimester_course_utils.assign_trimester_courses)
    assert 'student' in assign_sig.parameters, "assign_trimester_courses missing 'student' parameter"
    assert 'group_ids' in assign_sig.parameters, "assign_trimester_courses missing 'group_ids' parameter"
    
    conflicts_sig = inspect.signature(trimester_course_utils.get_trimester_course_conflicts)
    assert 'student' in conflicts_sig.parameters, "get_trimester_course_conflicts missing 'student' parameter"
    assert 'group_ids' in conflicts_sig.parameters, "get_trimester_course_conflicts missing 'group_ids' parameter"
    
    print("Utility functions verification passed!")

def check_core_requirements():
    """Verify that the core requirements of the trimester course system are met."""
    print("\nVerifying core requirements...")
    
    # Check that the 6th grade required pairs exist
    wh_hw_pair = TrimesterCourseGroup.objects.filter(name__icontains='World History').exists()
    cta_tac_pair = TrimesterCourseGroup.objects.filter(name__icontains='Computer Technology').exists()
    arts_group = TrimesterCourseGroup.objects.filter(name__icontains='Art').exists()
    
    assert wh_hw_pair, "Missing World History pair group"
    assert cta_tac_pair, "Missing Computer Technology pair group"
    assert arts_group, "Missing Arts Electives group"
    
    # Check that WH6/HW6 courses exist
    wh6_exists = Course.objects.filter(id__in=['WH6']).exists()
    hw6_exists = Course.objects.filter(id__in=['HW6']).exists()
    assert wh6_exists, "Missing WH6 course"
    assert hw6_exists, "Missing HW6 course"
    
    # Check that CTA6/TAC6 courses exist
    cta6_exists = Course.objects.filter(id__in=['CTA6']).exists()
    tac6_exists = Course.objects.filter(id__in=['TAC6']).exists()
    assert cta6_exists, "Missing CTA6 course"
    assert tac6_exists, "Missing TAC6 course"
    
    # Check that art elective courses exist
    art_courses_exist = Course.objects.filter(id__in=['WW6', 'Art6', 'Mus6']).count() > 0
    assert art_courses_exist, "Missing art elective courses"
    
    print("Core requirements verification passed!")

if __name__ == "__main__":
    verify_implementation()
    check_core_requirements() 