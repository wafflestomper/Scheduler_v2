from schedule.models import Student, Enrollment, Section

# Get a sample student
student = Student.objects.get(id=list(Student.objects.filter(grade_level=6).values_list('id', flat=True))[0])

# Get their enrollments in language courses
enrollments = Enrollment.objects.filter(student=student, section__course__type='language').select_related('section')

print(f'Student {student.name} assigned sections:')
for e in enrollments:
    print(f'- {e.section.course.name} (Trimester: {e.section.when}, Period: {e.section.period})')
