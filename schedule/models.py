from django.db import models

# Create your models here.

class Teacher(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)
    availability = models.TextField(help_text="Format: 'M1-M6,T1-T3'")
    subjects = models.TextField(help_text="Format: 'Math|Science'")

    def __str__(self):
        return f"{self.name} ({self.id})"

class Room(models.Model):
    ROOM_TYPES = [
        ('classroom', 'Classroom'),
        ('lab', 'Laboratory'),
        ('gym', 'Gymnasium'),
        ('art', 'Art Room'),
        ('music', 'Music Room'),
        ('other', 'Other'),
    ]
    
    id = models.CharField(max_length=10, primary_key=True)
    number = models.CharField(max_length=50)
    capacity = models.IntegerField()
    type = models.CharField(max_length=50, choices=ROOM_TYPES)

    def __str__(self):
        return f"Room {self.number} ({self.type})"

class Student(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)
    grade_level = models.IntegerField()
    preferences = models.TextField(help_text="Format: 'Art|Robotics'")

    def __str__(self):
        return f"{self.name} - Grade {self.grade_level}"
    
    def get_preferences_list(self):
        return self.preferences.split('|') if self.preferences else []

class Course(models.Model):
    COURSE_TYPES = [
        ('core', 'Core'),
        ('elective', 'Elective'),
        ('required_elective', 'Required Elective'),
        ('language', 'Language'),
    ]
    
    DURATION_TYPES = [
        ('year', 'Year'),
        ('trimester', 'Trimester'),
        ('quarter', 'Quarter'),
    ]
    
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=COURSE_TYPES)
    grade_level = models.IntegerField()
    max_students = models.IntegerField(null=True, blank=True)
    eligible_teachers = models.TextField(help_text="Format: 'T001|T002'")
    duration = models.CharField(max_length=10, choices=DURATION_TYPES, default='year')
    sections_needed = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()}) - Grade {self.grade_level}"
    
    def get_eligible_teachers_list(self):
        return self.eligible_teachers.split('|') if self.eligible_teachers else []

class Period(models.Model):
    DAY_CHOICES = [
        ('M', 'Monday'),
        ('T', 'Tuesday'),
        ('W', 'Wednesday'),
        ('TH', 'Thursday'),
        ('F', 'Friday'),
    ]
    
    id = models.CharField(max_length=10, primary_key=True)
    period_name = models.CharField(max_length=50, blank=True, null=True, help_text="Descriptive name for this period")
    days = models.TextField(default='M', help_text="Format: 'M|T|W' for Monday, Tuesday, Wednesday")
    slot = models.CharField(max_length=10, help_text="Period identifier (e.g., 1, 2, A, B, L for Lunch)")
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        if self.period_name:
            return f"{self.period_name} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"
        
        days_display = self.get_days_display()
        return f"{days_display} Period {self.slot} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"
    
    def get_days_list(self):
        return self.days.split('|') if self.days else []
    
    def get_days_display(self):
        days_list = self.get_days_list()
        if not days_list:
            return "No days"
        
        day_names = []
        day_dict = dict(self.DAY_CHOICES)
        for day_code in days_list:
            if day_code in day_dict:
                day_names.append(day_dict[day_code])
        
        if len(day_names) == 1:
            return day_names[0]
        elif len(day_names) == 2:
            return f"{day_names[0]} and {day_names[1]}"
        else:
            return ", ".join(day_names[:-1]) + f", and {day_names[-1]}"

class Section(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    section_number = models.IntegerField(default=1)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    students = models.ManyToManyField(Student, through='Enrollment', related_name='sections', blank=True)
    max_size = models.IntegerField(null=True, blank=True)
    exact_size = models.IntegerField(null=True, blank=True, help_text="If set, this section should have exactly this many students")
    when = models.CharField(max_length=20, default='year',
                          choices=[('year', 'Full Year'), 
                                  ('semester', 'Semester'),
                                  ('quarter', 'Quarter'),
                                  ('trimester', 'Trimester'),
                                  ('q1', 'Quarter 1'),
                                  ('q2', 'Quarter 2'),
                                  ('q3', 'Quarter 3'),
                                  ('q4', 'Quarter 4'),
                                  ('s1', 'Semester 1'),
                                  ('s2', 'Semester 2'),
                                  ('t1', 'Trimester 1'),
                                  ('t2', 'Trimester 2'),
                                  ('t3', 'Trimester 3'),
                                  ])
    
    def __str__(self):
        return f"{self.course.name} - Section {self.section_number}"
    
    def current_enrollment(self):
        return self.students.count()
    
    def get_students_list(self):
        """Get a list of student IDs enrolled in this section."""
        return list(self.students.values_list('id', flat=True))

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    date_enrolled = models.DateField(auto_now_add=True)
    
    class Meta:
        unique_together = [('student', 'section')]
        
    def __str__(self):
        return f"{self.student.name} enrolled in {self.section}"

class CourseEnrollment(models.Model):
    """Tracks students enrolled in courses (but not yet assigned to specific sections)"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='course_enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_enrollments')
    date_enrolled = models.DateField(auto_now_add=True)
    
    class Meta:
        unique_together = [('student', 'course')]
        
    def __str__(self):
        return f"{self.student.name} enrolled in {self.course.name}"

class CourseGroup(models.Model):
    """
    Groups related courses together for scheduling purposes.
    Used for courses that should be scheduled in the same period 
    but in different time segments (trimesters, quarters, semesters).
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    courses = models.ManyToManyField(Course, related_name='course_groups')
    preferred_period = models.ForeignKey(Period, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_courses_count(self):
        return self.courses.count()

class TrimesterCourseGroup(models.Model):
    """
    Groups trimester courses that need to be scheduled in a specific way:
    - Each student takes exactly one course from each group
    - All selected courses must be in different trimesters
    - All selected courses must be in the same period
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    GROUP_TYPES = [
        ('required_pair', 'Required Pair'),
        ('elective', 'Elective Options'),
    ]
    group_type = models.CharField(max_length=20, choices=GROUP_TYPES)
    
    courses = models.ManyToManyField(Course, related_name='trimester_groups')
    preferred_period = models.ForeignKey(Period, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_group_type_display()})"
    
    def get_courses_count(self):
        return self.courses.count()
