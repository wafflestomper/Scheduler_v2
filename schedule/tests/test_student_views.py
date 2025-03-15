from django.test import TestCase, Client
from django.urls import reverse
from schedule.models import Student, Section, Course, Period, Teacher, Enrollment
from django.contrib.messages import get_messages
import datetime


class StudentViewsTest(TestCase):
    def setUp(self):
        """Set up test data for student view tests"""
        self.client = Client()
        
        # Create test students
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
        
        # Create test period
        self.period = Period.objects.create(
            id="P1",
            period_name="Period 1",
            days="M",
            slot="1",
            start_time=datetime.time(8, 0),
            end_time=datetime.time(9, 0)
        )
        
        # Create test course
        self.course = Course.objects.create(
            id="MATH101",
            name="Algebra I",
            type="core",
            grade_level=9,
            max_students=30,
            duration="year",
            sections_needed=1
        )
        
        # Create test teacher
        self.teacher = Teacher.objects.create(
            id="T001",
            name="Mr. Smith",
            availability="M1-M6,T1-T6",
            subjects="Math"
        )
        
        # Create a section with the student1 enrolled
        self.section = Section.objects.create(
            id="MATH101-1",
            course=self.course,
            section_number=1,
            teacher=self.teacher,
            period=self.period,
            when="year"
        )
        
        # Add student1 to the section using the Enrollment model
        Enrollment.objects.create(
            student=self.student1,
            section=self.section
        )
    
    def test_view_students_list(self):
        """Test that the student list view displays correctly"""
        response = self.client.get(reverse('view_students'))
        
        # Check the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check that students are in the context
        self.assertIn('students_by_grade', response.context)
        self.assertIn('total_students', response.context)
        
        # Check the total count is correct
        self.assertEqual(response.context['total_students'], 2)
        
        # Check the student names are displayed
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Jane Smith')
    
    def test_view_students_with_grade_filter(self):
        """Test that the grade filter works"""
        # Filter for grade 9
        response = self.client.get(reverse('view_students') + '?grade=9')
        
        # Check the filtering works correctly
        self.assertEqual(response.context['total_students'], 1)
        self.assertContains(response, 'John Doe')
        self.assertNotContains(response, 'Jane Smith')
        
        # Check the grade filter is preserved in the context
        self.assertEqual(response.context['grade_filter'], '9')
    
    def test_view_students_with_search(self):
        """Test that the search filter works"""
        # Search for 'Jane'
        response = self.client.get(reverse('view_students') + '?search=Jane')
        
        # Check the filtering works correctly
        self.assertEqual(response.context['total_students'], 1)
        self.assertContains(response, 'Jane Smith')
        self.assertNotContains(response, 'John Doe')
        
        # Check the search query is preserved in the context
        self.assertEqual(response.context['search_query'], 'Jane')
    
    def test_student_detail(self):
        """Test viewing the details of a specific student"""
        response = self.client.get(reverse('student_detail', args=[self.student1.id]))
        
        # Check the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check the student is in the context
        self.assertIn('student', response.context)
        self.assertEqual(response.context['student'], self.student1)
        
        # Check the student's schedule is in the context
        self.assertIn('schedule', response.context)
        self.assertEqual(len(response.context['schedule']), 1)
        
        # Check the student data is displayed
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Grade 9')
        
        # Check the schedule information is displayed
        self.assertContains(response, 'Algebra I')
        self.assertContains(response, 'Mr. Smith')
    
    def test_student_detail_nonexistent(self):
        """Test viewing details for a non-existent student"""
        response = self.client.get(reverse('student_detail', args=['NONEXISTENT']))
        
        # Check redirect to student list
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('view_students')))
        
        # Follow the redirect and check for error message
        response = self.client.get(reverse('student_detail', args=['NONEXISTENT']), follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertGreaterEqual(len(messages), 1)  # There might be multiple messages
        
        # Check that at least one message contains 'Student not found'
        student_not_found_message = False
        for message in messages:
            if 'Student not found' in str(message):
                student_not_found_message = True
                break
        self.assertTrue(student_not_found_message, "No 'Student not found' message was found")
    
    def test_edit_student(self):
        """Test editing a student's information"""
        # GET request to edit page
        response = self.client.get(reverse('edit_student', args=[self.student2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane Smith')
        
        # POST updated data
        updated_data = {
            'id': 'S002',  # Keep the same ID
            'name': 'Jane Anderson',  # Changed name
            'grade_level': '11',  # Changed grade
            'preferences': 'Drama|Art'  # Changed preferences
        }
        
        response = self.client.post(reverse('edit_student', args=[self.student2.id]), updated_data, follow=True)
        
        # Check redirect to student detail
        self.assertRedirects(response, reverse('student_detail', args=[self.student2.id]))
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('updated successfully', str(messages[0]))
        
        # Check the student was updated in the database
        self.student2.refresh_from_db()
        self.assertEqual(self.student2.name, 'Jane Anderson')
        self.assertEqual(self.student2.grade_level, 11)
        self.assertEqual(self.student2.preferences, 'Drama|Art')
    
    def test_delete_student(self):
        """Test deleting a student"""
        # GET confirmation page
        response = self.client.get(reverse('delete_student', args=[self.student2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane Smith')
        self.assertContains(response, 'Are you sure')
        
        # POST to delete
        response = self.client.post(reverse('delete_student', args=[self.student2.id]), follow=True)
        
        # Check redirect to student list
        self.assertRedirects(response, reverse('view_students'))
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('deleted successfully', str(messages[0]))
        
        # Check the student no longer exists
        self.assertFalse(Student.objects.filter(id=self.student2.id).exists())
    
    def test_delete_student_with_section(self):
        """Test deleting a student who is enrolled in sections"""
        # Student1 is enrolled in a section
        # Make sure the enrollment exists
        self.assertTrue(Enrollment.objects.filter(student=self.student1, section=self.section).exists())
        
        # GET confirmation page
        response = self.client.get(reverse('delete_student', args=[self.student1.id]))
        self.assertEqual(response.status_code, 200)
        
        # POST to delete
        response = self.client.post(reverse('delete_student', args=[self.student1.id]), follow=True)
        
        # Check redirect to student list
        self.assertRedirects(response, reverse('view_students'))
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('deleted successfully', str(messages[0]))
        
        # Check the student no longer exists
        self.assertFalse(Student.objects.filter(id=self.student1.id).exists())
        
        # Check the enrollment no longer exists
        self.assertFalse(Enrollment.objects.filter(student__id=self.student1.id).exists()) 