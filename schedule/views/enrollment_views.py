from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from ..models import Student, Course, CourseEnrollment, Section, Enrollment
import json
from django.db.models import Q, Count
from django.db import transaction
from ..utils.section_registration_utils import clear_student_enrollments


def enroll_students(request):
    """View for managing student enrollments in courses"""
    # Get filter parameters
    grade_filter = request.GET.get('grade')
    course_ids = request.GET.getlist('course_id')
    
    # Get all available grades
    grades = list(Student.objects.values_list('grade_level', flat=True).distinct().order_by('grade_level'))
    
    # Base queryset for students
    students = Student.objects.all().order_by('name')
    
    # Filter students by grade if specified
    if grade_filter:
        students = students.filter(grade_level=grade_filter)
    
    # Get all courses for the filter dropdown
    courses = Course.objects.all().order_by('name')
    if grade_filter:
        courses = courses.filter(grade_level=grade_filter)
        
    # Get selected courses if specified
    selected_courses = []
    if course_ids:
        selected_courses = Course.objects.filter(id__in=course_ids)
    
    # Prepare student data with enrollment info
    student_data = []
    for student in students:
        # Count course enrollments
        enrolled_course_count = CourseEnrollment.objects.filter(student=student).count()
        
        # Count section registrations (actual section assignments)
        registered_section_count = Enrollment.objects.filter(student=student).count()
        
        # Check if student is enrolled in the selected courses
        enrolled_in_selected_course = False
        if selected_courses:
            # Check if enrolled in ANY of the selected courses
            enrolled_in_selected_course = CourseEnrollment.objects.filter(
                student=student,
                course__in=selected_courses
            ).exists()
        
        student_data.append({
            'student': student,
            'enrolled_course_count': enrolled_course_count,
            'registered_section_count': registered_section_count,
            'enrolled_in_selected_course': enrolled_in_selected_course
        })
    
    # Calculate enrollment statistics
    total_students = len(student_data)
    enrolled_students = sum(1 for data in student_data if data['enrolled_in_selected_course']) if selected_courses else sum(1 for data in student_data if data['enrolled_course_count'] > 0)
    available_students = total_students - enrolled_students
    
    context = {
        'grades': grades,
        'grade_filter': grade_filter,
        'courses': courses,
        'selected_course_ids': course_ids,
        'student_data': student_data,
        'total_students': total_students,
        'enrolled_students': enrolled_students,
        'available_students': available_students
    }
    
    return render(request, 'schedule/enroll_students.html', context)


def enroll_student_to_course(request):
    """API endpoint for enrolling/unenrolling a student from a course"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        action = data.get('action', 'enroll')
        
        if not student_id or not course_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        student = Student.objects.get(id=student_id)
        course = Course.objects.get(id=course_id)
        
        if action == 'enroll':
            # Check if the student is already enrolled in this course
            enrollment, created = CourseEnrollment.objects.get_or_create(
                student=student,
                course=course
            )
            
            if created:
                return JsonResponse({
                    'status': 'success', 
                    'message': f'{student.name} successfully enrolled in {course.name}'
                })
            else:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'{student.name} is already enrolled in {course.name}'
                })
                
        elif action == 'unenroll':
            # Try to find and delete the enrollment
            try:
                enrollment = CourseEnrollment.objects.get(
                    student=student,
                    course=course
                )
                enrollment.delete()
                
                # Also remove any section assignments for this course
                enrollments = Enrollment.objects.filter(
                    student=student,
                    section__course=course
                )
                enrollments.delete()
                
                return JsonResponse({
                    'status': 'success', 
                    'message': f'{student.name} successfully unenrolled from {course.name}'
                })
            except CourseEnrollment.DoesNotExist:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'{student.name} is not enrolled in {course.name}'
                })
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action'})
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Student.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Student not found'})
    except Course.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Course not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def batch_enroll_students(request):
    """API endpoint for enrolling multiple students to a course at once"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        course_id = data.get('course_id')
        
        if not student_ids or not course_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        course = Course.objects.get(id=course_id)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id)
                
                # Check if the student is already enrolled
                _, created = CourseEnrollment.objects.get_or_create(
                    student=student,
                    course=course
                )
                
                if created:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f'{student.name} is already enrolled in {course.name}')
                    
            except Student.DoesNotExist:
                error_count += 1
                errors.append(f'Student ID {student_id} not found')
            except Exception as e:
                error_count += 1
                errors.append(f'Error enrolling student ID {student_id}: {str(e)}')
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully enrolled {success_count} students in {course.name}',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Course.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Course not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def batch_disenroll_students(request):
    """API endpoint for disenrolling multiple students from a course at once"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        course_id = data.get('course_id')
        
        if not course_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required course_id parameter'})
        
        course = Course.objects.get(id=course_id)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id)
                
                # Try to find and delete the enrollment
                try:
                    enrollment = CourseEnrollment.objects.get(
                        student=student,
                        course=course
                    )
                    enrollment.delete()
                    
                    # Also remove any section assignments for this course
                    enrollments = Enrollment.objects.filter(
                        student=student,
                        section__course=course
                    )
                    enrollments.delete()
                    
                    success_count += 1
                except CourseEnrollment.DoesNotExist:
                    error_count += 1
                    errors.append(f'{student.name} is not enrolled in {course.name}')
                    
            except Student.DoesNotExist:
                error_count += 1
                errors.append(f'Student ID {student_id} not found')
            except Exception as e:
                error_count += 1
                errors.append(f'Error disenrolling student ID {student_id}: {str(e)}')
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully disenrolled {success_count} students from {course.name}',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Course.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Course not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def clear_student_enrollments_api(request):
    """API endpoint for clearing all section enrollments for one or more students"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        
        if not student_ids:
            return JsonResponse({'status': 'error', 'message': 'Missing required student_ids parameter'})
        
        success_count = 0
        error_count = 0
        errors = []
        
        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id)
                # Clear all enrollments for this student
                removed_count = clear_student_enrollments(student_id)
                success_count += 1
                
            except Student.DoesNotExist:
                error_count += 1
                errors.append(f"Student ID {student_id} not found")
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing student ID {student_id}: {str(e)}")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully cleared enrollments for {success_count} students',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def assign_students_to_sections(request):
    """API endpoint for assigning students to sections based on course enrollments"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        grade_level = data.get('grade_level')
        
        # Get course enrollments that need section assignments
        course_enrollments = CourseEnrollment.objects.all()
        if grade_level:
            course_enrollments = course_enrollments.filter(student__grade_level=grade_level)
        
        # Group enrollments by course to process each course separately
        courses = Course.objects.filter(
            id__in=course_enrollments.values_list('course_id', flat=True).distinct()
        )
        
        total_assigned = 0
        total_failures = 0
        errors = []
        
        with transaction.atomic():
            for course in courses:
                # Get students enrolled in this course
                enrollments = course_enrollments.filter(course=course)
                
                # Get available sections for this course
                sections = Section.objects.filter(course=course).prefetch_related('enrollments')
                
                if not sections.exists():
                    errors.append(f'No sections found for course {course.name}')
                    continue
                
                # Calculate available capacity for each section
                section_capacities = {}
                for section in sections:
                    enrolled_count = section.enrollments.count()
                    section_capacities[section.id] = {
                        'section': section,
                        'enrolled': enrolled_count,
                        'available': section.capacity - enrolled_count if section.capacity else float('inf')
                    }
                
                # Sort sections by available capacity (descending)
                sorted_sections = sorted(
                    section_capacities.values(),
                    key=lambda x: x['available'],
                    reverse=True
                )
                
                # Assign students to sections based on available capacity
                for enrollment in enrollments:
                    student = enrollment.student
                    
                    # Skip if student is already assigned to a section for this course
                    if Enrollment.objects.filter(student=student, section__course=course).exists():
                        continue
                    
                    # Find a section with available capacity
                    assigned = False
                    for section_data in sorted_sections:
                        section = section_data['section']
                        if section_data['available'] > 0:
                            # Create enrollment
                            Enrollment.objects.create(
                                student=student,
                                section=section
                            )
                            # Update available capacity
                            section_data['enrolled'] += 1
                            section_data['available'] -= 1
                            assigned = True
                            total_assigned += 1
                            break
                    
                    if not assigned:
                        total_failures += 1
                        errors.append(f'Could not assign {student.name} to any section for {course.name} - all sections full')
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully assigned {total_assigned} students to sections. {total_failures} students could not be assigned.',
            'assigned_count': total_assigned,
            'failure_count': total_failures,
            'errors': errors[:20]  # Limit error messages to avoid overwhelming response
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}) 