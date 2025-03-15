from django.test import TestCase, Client
from django.urls import reverse
from schedule.models import Course, Section, Period
from django.contrib.messages import get_messages
import datetime


class CourseViewsTest(TestCase):
    def setUp(self):
        """Set up test data for course views tests"""
        self.client = Client()
        
        # Create test courses
        self.course1 = Course.objects.create(
            id="MATH101",
            name="Algebra I",
            type="core",
            grade_level=9,
            max_students=30,
            duration="year",
            sections_needed=2
        )
        
        self.course2 = Course.objects.create(
            id="SCI102",
            name="Biology",
            type="core",
            grade_level=9,
            max_students=25,
            duration="year",
            sections_needed=1
        )
        
        # Course data for creating a new course
        self.new_course_data = {
            'course_id': 'ENG101',
            'name': 'English Literature',
            'type': 'core',
            'grade_level': '10',
            'max_students': '30',
            'duration': 'year',
            'sections_needed': '2',
            'eligible_teachers': 'T001|T002'
        }
        
        # Create a period first
        self.period = Period.objects.create(
            id="P1",
            period_name="Period 1",
            days="M",
            slot="1",
            start_time=datetime.time(8, 0),  # 8:00 AM
            end_time=datetime.time(9, 0)     # 9:00 AM
        )
        
        # Create a section using course1 (to test deletion constraints)
        self.section = Section.objects.create(
            id="MATH101-01",
            course=self.course1,
            section_number=1,
            period=self.period,
            when="year",
        )
    
    def test_view_courses(self):
        """Test that the course list view displays correctly"""
        response = self.client.get(reverse('view_courses'))
        
        # Check the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check that courses are in the context
        self.assertIn('courses', response.context)
        
        # Check that both test courses are in the context
        courses = list(response.context['courses'])
        self.assertEqual(len(courses), 2)
        
        # Check the course names are displayed
        self.assertContains(response, 'Algebra I')
        self.assertContains(response, 'Biology')
    
    def test_create_course(self):
        """Test creating a new course"""
        # GET request should return the form
        response = self.client.get(reverse('create_course'))
        self.assertEqual(response.status_code, 200)
        
        # POST new course data
        response = self.client.post(reverse('create_course'), self.new_course_data, follow=True)
        
        # Check redirect to view_courses
        self.assertRedirects(response, reverse('view_courses'))
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('created successfully', str(messages[0]))
        
        # Check the course was created in the database
        self.assertTrue(Course.objects.filter(id='ENG101').exists())
        new_course = Course.objects.get(id='ENG101')
        self.assertEqual(new_course.name, 'English Literature')
    
    def test_edit_course(self):
        """Test editing an existing course"""
        # GET request should return the form with course data
        response = self.client.get(reverse('edit_course', args=[self.course2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Biology')
        
        # POST updated course data
        updated_data = {
            'name': 'Advanced Biology',
            'type': 'core',
            'grade_level': '10',
            'max_students': '20',
            'duration': 'year',
            'sections_needed': '2',
            'eligible_teachers': 'T003'
        }
        
        response = self.client.post(reverse('edit_course', args=[self.course2.id]), updated_data, follow=True)
        
        # Check redirect to view_courses
        self.assertRedirects(response, reverse('view_courses'))
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('updated successfully', str(messages[0]))
        
        # Check the course was updated in the database
        self.course2.refresh_from_db()
        self.assertEqual(self.course2.name, 'Advanced Biology')
        self.assertEqual(self.course2.max_students, 20)
        self.assertEqual(self.course2.eligible_teachers, 'T003')
    
    def test_delete_course_with_sections(self):
        """Test that a course with sections cannot be deleted"""
        # GET request should show the confirmation page
        response = self.client.get(reverse('delete_course', args=[self.course1.id]))
        self.assertEqual(response.status_code, 200)
        
        # There should be a warning about sections
        self.assertContains(response, 'Cannot Delete Course')
        self.assertContains(response, 'section')
        
        # POST to try to delete the course
        response = self.client.post(reverse('delete_course', args=[self.course1.id]), follow=True)
        
        # Check redirect to view_courses
        self.assertRedirects(response, reverse('view_courses'))
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Cannot delete', str(messages[0]))
        
        # Check the course still exists
        self.assertTrue(Course.objects.filter(id=self.course1.id).exists())
    
    def test_delete_course_without_sections(self):
        """Test deleting a course that has no sections"""
        # GET request should show the confirmation page
        response = self.client.get(reverse('delete_course', args=[self.course2.id]))
        self.assertEqual(response.status_code, 200)
        
        # There should be a warning 
        self.assertContains(response, 'Warning')
        self.assertContains(response, 'Are you sure')
        
        # POST to delete the course
        response = self.client.post(reverse('delete_course', args=[self.course2.id]), follow=True)
        
        # Check redirect to view_courses
        self.assertRedirects(response, reverse('view_courses'))
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('deleted successfully', str(messages[0]))
        
        # Check the course no longer exists
        self.assertFalse(Course.objects.filter(id=self.course2.id).exists()) 