from schedule.models import Student, CourseEnrollment, Course

student = Student.objects.get(id=list(Student.objects.filter(grade_level=6).values_list('id', flat=True))[0])
enrollments = CourseEnrollment.objects.filter(student=student, course__type='language')
print(f'Student {student.name} enrollments:')
for e in enrollments:
    print(f'- {e.course.name}')
