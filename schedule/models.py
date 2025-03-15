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
    ]
    
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=COURSE_TYPES)
    grade_level = models.IntegerField()
    max_students = models.IntegerField()
    eligible_teachers = models.TextField(help_text="Format: 'T001|T002'")

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
    id = models.CharField(max_length=50, primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    students = models.TextField(blank=True, help_text="Format: 'S001|S002'")
    
    class Meta:
        unique_together = [
            ('teacher', 'period'),  # A teacher can't teach multiple sections in the same period
            ('room', 'period'),     # A room can't be used for multiple sections in the same period
        ]
    
    def __str__(self):
        return f"{self.course.name} - {self.teacher.name} - {self.period}"
    
    def get_students_list(self):
        return self.students.split('|') if self.students else []
    
    def add_student(self, student_id):
        students_list = self.get_students_list()
        if student_id not in students_list:
            students_list.append(student_id)
            self.students = '|'.join(students_list)
            self.save()
    
    def remove_student(self, student_id):
        students_list = self.get_students_list()
        if student_id in students_list:
            students_list.remove(student_id)
            self.students = '|'.join(students_list)
            self.save()
