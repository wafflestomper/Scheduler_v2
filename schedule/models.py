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
    max_students = models.IntegerField()
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
    day = models.CharField(max_length=2, choices=DAY_CHOICES)
    slot = models.IntegerField(help_text="Period number (1-6)")
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.get_day_display()} Period {self.slot} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"

class Section(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    section_number = models.IntegerField(default=1)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    students = models.ManyToManyField(Student, through='Enrollment', related_name='sections', blank=True)
    max_size = models.IntegerField(null=True, blank=True)
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

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    date_enrolled = models.DateField(auto_now_add=True)
    
    class Meta:
        unique_together = [('student', 'section')]
        
    def __str__(self):
        return f"{self.student.name} enrolled in {self.section}"
