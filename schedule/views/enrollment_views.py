from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from ..models import Student, Course, CourseEnrollment, Section, Enrollment
import json
from django.db.models import Q, Count
from django.db import transaction
from ..utils.section_registration_utils import clear_student_enrollments
from ..services.enrollment_services.enrollment_service import EnrollmentService
from ..services.enrollment_services.course_enrollment_service import CourseEnrollmentService
from ..services.enrollment_services.section_assignment_service import SectionAssignmentService
from ..services.enrollment_services.batch_operations_service import BatchOperationsService


def enroll_students(request):
    """View for managing student enrollments in courses"""
    # Get filter parameters
    grade_filter = request.GET.get('grade')
    course_ids = request.GET.getlist('course_id')
    
    # Get all available grades
    grades = list(Student.objects.values_list('grade_level', flat=True).distinct().order_by('grade_level'))
    
    # Get all courses for the filter dropdown
    courses = Course.objects.all().order_by('name')
    if grade_filter:
        courses = courses.filter(grade_level=grade_filter)
    
    # Get student data with enrollment info
    result = CourseEnrollmentService.get_enrolled_students_with_counts(grade_filter, course_ids)
    
    context = {
        'grades': grades,
        'selected_grade': grade_filter,
        'courses': courses,
        'selected_course_ids': course_ids,
        'student_data': result['students'],
        'total_students': result['total_count']
    }
    
    return render(request, 'schedule/enroll_students.html', context)


def enroll_student_in_course(request):
    """API endpoint for enrolling a student in a course"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        
        if not student_id or not course_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        result = CourseEnrollmentService.enroll_student_in_course(student_id, course_id)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def remove_student_from_course(request):
    """API endpoint for removing a student from a course"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        
        if not student_id or not course_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        result = CourseEnrollmentService.remove_student_from_course(student_id, course_id)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def bulk_enroll_students_in_course(request):
    """API endpoint for enrolling multiple students in a course"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        course_id = data.get('course_id')
        
        if not student_ids or not course_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        result = CourseEnrollmentService.bulk_enroll_students_in_course(student_ids, course_id)
        
        return JsonResponse({
            'status': 'success' if result['success'] else 'error',
            'message': result['message'],
            'success_count': result['success_count'],
            'error_count': result['error_count'],
            'errors': result['errors']
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def enroll_grade_in_course(request):
    """API endpoint for enrolling all students in a grade level in a course"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        grade_level = data.get('grade_level')
        course_id = data.get('course_id')
        
        if grade_level is None or not course_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        result = BatchOperationsService.enroll_grade_in_course(grade_level, course_id)
        
        return JsonResponse({
            'status': 'success' if result['success'] else 'error',
            'message': result['message'],
            'success_count': result['success_count'],
            'error_count': result['error_count'],
            'errors': result['errors']
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
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
        
        result = BatchOperationsService.clear_all_enrollments_for_students(student_ids)
        
        return JsonResponse({
            'status': 'success' if result['success'] else 'error',
            'message': result['message'],
            'success_count': result['success_count'],
            'error_count': result['error_count'],
            'errors': result['errors']
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
        
        result = SectionAssignmentService.assign_students_to_sections(grade_level)
        
        return JsonResponse({
            'status': 'success' if result['success'] else 'error',
            'message': result['message'],
            'total_assigned': result['total_assigned'],
            'total_failures': result['total_failures'],
            'errors': result['errors'][:10]  # Limit to first 10 errors to keep response size manageable
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def assign_student_to_course_section(request):
    """API endpoint for assigning a student to an available section for a course"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        
        if not student_id or not course_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        result = SectionAssignmentService.assign_student_to_course_section(student_id, course_id)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'section_id': result['section'].id
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def enroll_student_in_section(request):
    """API endpoint for enrolling a student in a specific section"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        section_id = data.get('section_id')
        
        if not student_id or not section_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        # Check for conflicts
        conflicts = EnrollmentService.get_conflicts_for_enrollment(student_id, section_id)
        
        if conflicts['has_conflicts']:
            return JsonResponse({
                'status': 'error',
                'message': 'Cannot enroll student due to conflicts',
                'conflicts': conflicts['conflicts']
            })
        
        # Enroll the student
        result = EnrollmentService.enroll_student_in_section(student_id, section_id)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def remove_student_from_section(request):
    """API endpoint for removing a student from a section"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        section_id = data.get('section_id')
        
        if not student_id or not section_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        result = EnrollmentService.remove_student_from_section(student_id, section_id)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'message': result['message']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result['message']
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def bulk_enroll_students_in_section(request):
    """API endpoint for enrolling multiple students in a section"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        section_id = data.get('section_id')
        
        if not student_ids or not section_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})
        
        result = BatchOperationsService.bulk_enroll_students_in_sections(student_ids, section_id)
        
        return JsonResponse({
            'status': 'success' if result['success'] else 'error',
            'message': result['message'],
            'success_count': result['success_count'],
            'error_count': result['error_count'],
            'errors': result['errors']
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}) 