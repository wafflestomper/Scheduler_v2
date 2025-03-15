from django.test import TestCase, Client
from django.urls import reverse
from schedule.models import Student, Section, Course, Period, Teacher, Enrollment
import datetime


class AdminReportsTest(TestCase):
    def setUp(self):
        """Set up test data for admin reports tests"""
        self.client = Client()
        
        # Create test students in different grades
        self.student1 = Student.objects.create(
            id="S001",
            name="John Doe",
            grade_level=9,
            preferences="Math|Science"
        )
        
        self.student2 = Student.objects.create(
            id="S002",
            name="Jane Smith",
            grade_level=10,
            preferences="Art|Music"
        )
        
        self.student3 = Student.objects.create(
            id="S003",
            name="Bob Johnson",
            grade_level=9,
            preferences="History|Science"
        )
        
        # Create test period
        self.period = Period.objects.create(
            id="P1",
            period_name="Period 1",
            days="M",
            slot="1",
            start_time=datetime.time(8, 0),
            end_time=datetime.time(9, 0)
        )
        
        # Create test courses
        self.course1 = Course.objects.create(
            id="MATH101",
            name="Algebra I",
            type="core",
            grade_level=9,
            max_students=30,
            duration="year",
            sections_needed=1
        )
        
        self.course2 = Course.objects.create(
            id="ENG101",
            name="English Literature",
            type="core",
            grade_level=10,
            max_students=25,
            duration="year",
            sections_needed=1
        )
        
        # Create test teachers
        self.teacher1 = Teacher.objects.create(
            id="T001",
            name="Mr. Smith",
            availability="M1-M6,T1-T6",
            subjects="Math"
        )
        
        self.teacher2 = Teacher.objects.create(
            id="T002",
            name="Ms. Johnson",
            availability="M1-M6,W1-W6",
            subjects="English"
        )
        
        # Create sections with students enrolled
        self.section1 = Section.objects.create(
            id="MATH101-1",
            course=self.course1,
            section_number=1,
            teacher=self.teacher1,
            period=self.period,
            when="year"
        )
        
        # Add students to math section using Enrollment model
        Enrollment.objects.create(student=self.student1, section=self.section1)
        Enrollment.objects.create(student=self.student3, section=self.section1)
        
        self.section2 = Section.objects.create(
            id="ENG101-1",
            course=self.course2,
            section_number=1,
            teacher=self.teacher2,
            period=self.period,
            when="year"
        )
        
        # Add student to english section using Enrollment model
        Enrollment.objects.create(student=self.student2, section=self.section2)
        
        # Create a section without a teacher
        self.section3 = Section.objects.create(
            id="MATH101-2",
            course=self.course1,
            section_number=2,
            teacher=None,  # No teacher assigned
            period=self.period,
            when="year"
        )
    
    def test_admin_reports_view(self):
        """Test that the admin reports view loads correctly"""
        response = self.client.get(reverse('admin_reports'))
        
        # Check the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check the context contains all the required data
        self.assertIn('enrollment_by_grade', response.context)
        self.assertIn('total_students', response.context)
        self.assertIn('course_enrollment', response.context)
        self.assertIn('teacher_load', response.context)
        
        # Check the total student count is correct
        self.assertEqual(response.context['total_students'], 3)
        
        # Check enrollment by grade
        enrollment_by_grade = response.context['enrollment_by_grade']
        self.assertEqual(enrollment_by_grade[9], 2)  # 2 students in grade 9
        self.assertEqual(enrollment_by_grade[10], 1)  # 1 student in grade 10
        
        # Check course enrollment data
        course_enrollment = response.context['course_enrollment']
        self.assertEqual(course_enrollment['MATH101']['total_students'], 2)
        self.assertEqual(course_enrollment['ENG101']['total_students'], 1)
        
        # Check teacher load data
        teacher_load = response.context['teacher_load']
        self.assertEqual(teacher_load['T001']['total_students'], 2)
        self.assertEqual(teacher_load['T002']['total_students'], 1)
        
        # Check that the enrollment chart is included in the template
        self.assertContains(response, 'enrollmentChart')
        
        # Check that the course table is included
        self.assertContains(response, 'courseTable')
        
        # Check that the teacher table is included
        self.assertContains(response, 'teacherTable')
        
        # Check that course names are displayed
        self.assertContains(response, 'Algebra I')
        self.assertContains(response, 'English Literature')
        
        # Check that teacher names are displayed
        self.assertContains(response, 'Mr. Smith')
        self.assertContains(response, 'Ms. Johnson')
        
        # Check that export links are included
        self.assertContains(response, 'Student Schedules')
        self.assertContains(response, 'Master Schedule')
    
    def test_admin_reports_chart_data(self):
        """Test that the chart data in the admin reports is correct"""
        response = self.client.get(reverse('admin_reports'))
        
        # Check that chart.js is included
        self.assertContains(response, 'chart.js')
        
        # Check that grade labels are included in the chart data
        self.assertContains(response, 'Grade 9')
        self.assertContains(response, 'Grade 10')
        
        # Check that the chart data values are included
        self.assertContains(response, '2,')  # 2 students in grade 9
        self.assertContains(response, '1,')  # 1 student in grade 10 