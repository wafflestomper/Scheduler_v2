#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_scheduler.settings")
django.setup()

from schedule.models import Student, Course, CourseGroup, Period, Section, Enrollment, CourseEnrollment
from django.db.models import Count

def schedule_6th_grade_language_courses():
    """
    Specialized algorithm for scheduling 6th-grade language courses.
    Requirements:
    - Students must take each language course (SPA6, CHI6, FRE6) in a different trimester
    - All language courses must be scheduled in the same period for a given student
    - Balance student distribution across sections
    """
    print("Starting 6th grade language course scheduling...")
    
    # 1. Identify the language courses
    language_courses = Course.objects.filter(id__in=['SPA6', 'CHI6', 'FRE6'])
    if language_courses.count() != 3:
        print(f"Error: Expected 3 language courses, found {language_courses.count()}")
        return False
    
    # 2. Get all 6th grade students enrolled in these language courses
    language_enrollments = CourseEnrollment.objects.filter(
        course__in=language_courses,
        student__grade_level=6
    ).select_related('student', 'course')
    
    # Group enrollments by student to find students enrolled in all three language courses
    student_enrollments = {}
    for enrollment in language_enrollments:
        if enrollment.student.id not in student_enrollments:
            student_enrollments[enrollment.student.id] = []
        student_enrollments[enrollment.student.id].append(enrollment)
    
    # Filter for students enrolled in all three language courses
    full_language_students = {}
    for student_id, enrollments in student_enrollments.items():
        if len(enrollments) == 3:  # Student is enrolled in all three language courses
            full_language_students[student_id] = enrollments
    
    print(f"Found {len(full_language_students)} 6th grade students enrolled in all three language courses")
    
    # 3. Get all available sections for these courses
    spa_sections = Section.objects.filter(course__id='SPA6').select_related('period')
    chi_sections = Section.objects.filter(course__id='CHI6').select_related('period')
    fre_sections = Section.objects.filter(course__id='FRE6').select_related('period')
    
    # Organize sections by period and trimester
    sections_by_period_trimester = {}
    for section_list in [spa_sections, chi_sections, fre_sections]:
        for section in section_list:
            period_id = section.period_id
            trimester = section.when
            
            if period_id not in sections_by_period_trimester:
                sections_by_period_trimester[period_id] = {}
            
            if trimester not in sections_by_period_trimester[period_id]:
                sections_by_period_trimester[period_id][trimester] = {}
            
            sections_by_period_trimester[period_id][trimester][section.course_id] = {
                'section': section,
                'current_enrollment': section.students.count(),
                'max_capacity': section.course.max_students
            }
    
    # 4. Create a CourseGroup if it doesn't exist
    language_group, created = CourseGroup.objects.get_or_create(
        name="6th Grade Languages",
        defaults={'description': "Group for 6th grade language courses (SPA6, CHI6, FRE6)"}
    )
    
    # Add courses to group if needed
    for course in language_courses:
        language_group.courses.add(course)
    
    # 5. Get sections that have all three language courses in different trimesters
    valid_period_assignments = []
    for period_id, trimesters in sections_by_period_trimester.items():
        # Check if this period has all three courses across different trimesters
        all_courses_covered = set()
        for trimester, courses in trimesters.items():
            all_courses_covered.update(courses.keys())
        
        if len(all_courses_covered) == 3:  # All three language courses are available
            valid_period_assignments.append(period_id)
    
    print(f"Found {len(valid_period_assignments)} periods with all three language courses in different trimesters")
    
    # 6. Schedule students
    assignment_success = 0
    assignment_failure = 0
    
    for student_id, enrollments in full_language_students.items():
        student = Student.objects.get(id=student_id)
        
        # Check if student already has any language section assignments
        existing_assignments = Enrollment.objects.filter(
            student_id=student_id,
            section__course__in=language_courses
        )
        
        if existing_assignments.exists():
            # Student already has some assignments, validate and complete them
            existing_period = None
            assigned_trimesters = {}
            assigned_courses = {}
            
            for enrollment in existing_assignments:
                section = enrollment.section
                course_id = section.course_id
                trimester = section.when
                period_id = section.period_id
                
                assigned_courses[course_id] = {
                    'section': section,
                    'trimester': trimester,
                    'period': period_id
                }
                
                if existing_period is None:
                    existing_period = period_id
                elif existing_period != period_id:
                    print(f"Warning: Student {student.name} has language courses in different periods")
                
                assigned_trimesters[trimester] = course_id
            
            # Complete missing assignments if possible
            if existing_period in sections_by_period_trimester:
                missing_courses = set(['SPA6', 'CHI6', 'FRE6']) - set(assigned_courses.keys())
                available_trimesters = set(['t1', 't2', 't3']) - set(assigned_trimesters.keys())
                
                if len(missing_courses) == len(available_trimesters):
                    # We can complete the assignment
                    for course_id in missing_courses:
                        # Find a section in an available trimester
                        for trimester in available_trimesters:
                            if (trimester in sections_by_period_trimester[existing_period] and 
                                course_id in sections_by_period_trimester[existing_period][trimester]):
                                section_data = sections_by_period_trimester[existing_period][trimester][course_id]
                                
                                if section_data['current_enrollment'] < section_data['max_capacity']:
                                    # Create enrollment
                                    Enrollment.objects.create(
                                        student=student,
                                        section=section_data['section']
                                    )
                                    
                                    # Update section count
                                    section_data['current_enrollment'] += 1
                                    assignment_success += 1
                                    
                                    print(f"Completed assignment for {student.name}: {course_id} in {trimester}")
                                    
                                    # Mark this trimester as used
                                    available_trimesters.remove(trimester)
                                    break
                else:
                    assignment_failure += 1
                    print(f"Cannot complete assignments for {student.name}: mismatched missing courses and trimesters")
        else:
            # New assignment - find a period with availability in all three trimesters
            best_period = None
            lowest_max_enrollment = float('inf')
            
            for period_id in valid_period_assignments:
                # Calculate maximum enrollment across all sections for this period
                max_enrollment = 0
                valid_assignment = True
                
                for trimester in ['t1', 't2', 't3']:
                    if trimester in sections_by_period_trimester[period_id]:
                        for course_id in ['SPA6', 'CHI6', 'FRE6']:
                            if course_id in sections_by_period_trimester[period_id][trimester]:
                                section_data = sections_by_period_trimester[period_id][trimester][course_id]
                                if section_data['current_enrollment'] >= section_data['max_capacity']:
                                    valid_assignment = False
                                max_enrollment = max(max_enrollment, section_data['current_enrollment'])
                
                if valid_assignment and max_enrollment < lowest_max_enrollment:
                    best_period = period_id
                    lowest_max_enrollment = max_enrollment
            
            if best_period is not None:
                # Assign student to each language course in a different trimester
                course_assignment = {}
                
                # Sort courses by enrollment to balance sections
                sorted_course_assignments = []
                for course_id in ['SPA6', 'CHI6', 'FRE6']:
                    for trimester in ['t1', 't2', 't3']:
                        if (trimester in sections_by_period_trimester[best_period] and 
                            course_id in sections_by_period_trimester[best_period][trimester]):
                            section_data = sections_by_period_trimester[best_period][trimester][course_id]
                            sorted_course_assignments.append((course_id, trimester, section_data))
                
                # Sort by enrollment (lowest first)
                sorted_course_assignments.sort(key=lambda x: x[2]['current_enrollment'])
                
                # Assign courses to trimesters
                assigned_trimesters = set()
                assigned_courses = set()
                
                for course_id, trimester, section_data in sorted_course_assignments:
                    if (course_id not in assigned_courses and 
                        trimester not in assigned_trimesters and 
                        section_data['current_enrollment'] < section_data['max_capacity']):
                        
                        # Create enrollment
                        Enrollment.objects.create(
                            student=student,
                            section=section_data['section']
                        )
                        
                        # Update section count
                        section_data['current_enrollment'] += 1
                        assigned_trimesters.add(trimester)
                        assigned_courses.add(course_id)
                        
                        print(f"Assigned {student.name} to {course_id} in {trimester}")
                
                if len(assigned_courses) == 3:
                    assignment_success += 1
                else:
                    assignment_failure += 1
                    print(f"Could not assign all three language courses for {student.name}")
            else:
                assignment_failure += 1
                print(f"No valid period assignment found for {student.name}")
    
    print(f"Language course scheduling complete. Success: {assignment_success}, Failure: {assignment_failure}")
    return True

if __name__ == "__main__":
    schedule_6th_grade_language_courses() 