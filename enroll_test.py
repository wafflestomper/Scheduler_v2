from schedule.models import Student, Course, CourseEnrollment

student_ids = Student.objects.filter(grade_level=6).values_list('id', flat=True)[:5]
language_courses = Course.objects.filter(id__in=['SPA6', 'CHI6', 'FRE6'])
for student_id in student_ids:
    student = Student.objects.get(id=student_id)
    for course in language_courses:
        CourseEnrollment.objects.get_or_create(student=student, course=course)
    print(f'Enrolled student {student.name} in all 3 language courses')
