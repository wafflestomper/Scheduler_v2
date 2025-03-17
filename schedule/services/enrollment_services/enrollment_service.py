from ...models import Student, Section, Enrollment
from django.db import transaction
from django.shortcuts import get_object_or_404


class EnrollmentService:
    """Service class for handling enrollment operations."""
    
    @staticmethod
    def get_student_enrollments(student_id):
        """Get all section enrollments for a student."""
        student = get_object_or_404(Student, pk=student_id)
        enrollments = Enrollment.objects.filter(student=student).select_related(
            'section', 'section__course', 'section__teacher', 'section__period', 'section__room'
        )
        
        return {
            'student': student,
            'enrollments': enrollments,
            'count': enrollments.count()
        }
    
    @staticmethod
    def get_section_enrollments(section_id):
        """Get all student enrollments for a section."""
        section = get_object_or_404(Section, pk=section_id)
        enrollments = Enrollment.objects.filter(section=section).select_related('student')
        
        return {
            'section': section,
            'enrollments': enrollments,
            'count': enrollments.count(),
            'capacity': section.max_size
        }
    
    @staticmethod
    def enroll_student_in_section(student_id, section_id):
        """Enroll a student in a section."""
        student = get_object_or_404(Student, pk=student_id)
        section = get_object_or_404(Section, pk=section_id)
        
        # Check if the student is already enrolled
        if Enrollment.objects.filter(student=student, section=section).exists():
            return {
                'success': False,
                'message': f"Student {student.name} is already enrolled in this section"
            }
        
        # Check if the section is at capacity
        if section.max_size and section.enrollments.count() >= section.max_size:
            return {
                'success': False,
                'message': f"Section is at capacity ({section.max_size} students)"
            }
        
        # Enroll the student
        enrollment = Enrollment.objects.create(student=student, section=section)
        
        return {
            'success': True,
            'message': f"Student {student.name} enrolled in {section.course.name} section {section.section_number}",
            'enrollment': enrollment
        }
    
    @staticmethod
    def remove_student_from_section(student_id, section_id):
        """Remove a student from a section."""
        student = get_object_or_404(Student, pk=student_id)
        section = get_object_or_404(Section, pk=section_id)
        
        # Check if the student is enrolled
        enrollment = Enrollment.objects.filter(student=student, section=section).first()
        if not enrollment:
            return {
                'success': False,
                'message': f"Student {student.name} is not enrolled in this section"
            }
        
        # Remove the enrollment
        enrollment.delete()
        
        return {
            'success': True,
            'message': f"Student {student.name} removed from {section.course.name} section {section.section_number}"
        }
    
    @staticmethod
    def clear_student_enrollments(student_id):
        """Clear all enrollments for a student."""
        student = get_object_or_404(Student, pk=student_id)
        
        # Count enrollments before deletion
        enrollment_count = Enrollment.objects.filter(student=student).count()
        
        # Delete all enrollments
        Enrollment.objects.filter(student=student).delete()
        
        return {
            'success': True,
            'message': f"Cleared {enrollment_count} enrollments for {student.name}",
            'count': enrollment_count
        }
    
    @staticmethod
    def clear_section_enrollments(section_id):
        """Clear all enrollments for a section."""
        section = get_object_or_404(Section, pk=section_id)
        
        # Count enrollments before deletion
        enrollment_count = Enrollment.objects.filter(section=section).count()
        
        # Delete all enrollments
        Enrollment.objects.filter(section=section).delete()
        
        return {
            'success': True,
            'message': f"Cleared {enrollment_count} enrollments for {section.course.name} section {section.section_number}",
            'count': enrollment_count
        }
    
    @staticmethod
    def get_conflicts_for_enrollment(student_id, section_id):
        """Check for conflicts when enrolling a student in a section."""
        student = get_object_or_404(Student, pk=student_id)
        section = get_object_or_404(Section, pk=section_id)
        
        conflicts = []
        
        # Skip conflict check if section has no period assigned
        if not section.period:
            return {
                'has_conflicts': False,
                'conflicts': []
            }
        
        # Check for period conflicts (student enrolled in other sections in the same period)
        student_sections = Enrollment.objects.filter(
            student=student, 
            section__period=section.period
        ).exclude(section_id=section_id).select_related('section', 'section__course')
        
        for enrollment in student_sections:
            conflicts.append({
                'type': 'period',
                'message': f"Student already enrolled in {enrollment.section.course.name} section {enrollment.section.section_number} during this period"
            })
        
        return {
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts
        } 