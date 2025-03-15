from schedule.models import Student, Enrollment, Section

# Check for all test students
student_ids = Student.objects.filter(grade_level=6).values_list("id", flat=True)[:5]

for student_id in student_ids:
    student = Student.objects.get(id=student_id)
    # Get their enrollments in language courses
    enrollments = Enrollment.objects.filter(student=student, section__course__type="language").select_related("section")
    
    print(f"Student {student.name} assigned sections:")
    for e in enrollments:
        print(f"- {e.section.course.name} (Trimester: {e.section.when}, Period: {e.section.period.id})")
        
    # Check if all enrollments have the same period
    periods = set([e.section.period.id for e in enrollments])
    print(f"Periods used: {periods}")
    print(f"All same period: {len(periods) == 1}")
    
    # Check if all enrollments have different trimesters
    trimesters = [e.section.when for e in enrollments]
    print(f"Trimesters used: {trimesters}")
    print(f"All different trimesters: {len(trimesters) == len(set(trimesters))}")    

