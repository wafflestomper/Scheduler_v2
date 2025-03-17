import os
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from schedule.models import Student, Teacher, Room, Course, Period, Section

class CSVUploadTestCase(TestCase):
    """Test cases for CSV upload functionality"""
    
    def setUp(self):
        """Set up the test client and test data paths"""
        self.client = Client()
        self.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        
    def get_test_file_path(self, filename):
        """Helper method to get the full path of a test file"""
        return os.path.join(self.test_data_dir, filename)
    
    def create_uploaded_file(self, filepath):
        """Helper method to create a SimpleUploadedFile from a file path"""
        with open(filepath, 'rb') as f:
            content = f.read()
        filename = os.path.basename(filepath)
        return SimpleUploadedFile(filename, content, content_type='text/csv')
    
    def test_student_upload(self):
        """Test uploading student CSV data"""
        # Check initial count
        initial_count = Student.objects.count()
        
        # Prepare the CSV file
        test_file_path = self.get_test_file_path('students_test.csv')
        csv_file = self.create_uploaded_file(test_file_path)
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'students', 'csv_file': csv_file},
            follow=True
        )
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed')
        self.assertContains(response, 'students')
        self.assertTrue(Student.objects.count() > initial_count)
        
        # Check a specific student was created correctly
        student = Student.objects.get(id='S001')
        self.assertIn('John', student.name)
        self.assertIn('Doe', student.name)
        self.assertEqual(student.grade_level, 6)
    
    def test_teacher_upload(self):
        """Test uploading teacher CSV data"""
        # Clear any existing teachers
        Teacher.objects.all().delete()
        
        # Check initial count
        initial_count = Teacher.objects.count()
        self.assertEqual(initial_count, 0)  # Ensure we start with 0 teachers
        
        # Prepare the CSV file
        test_file_path = self.get_test_file_path('teachers_test.csv')
        csv_file = self.create_uploaded_file(test_file_path)
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'teachers', 'csv_file': csv_file},
            follow=True
        )
        
        # Debug: Print response content
        print("Response content:", response.content.decode('utf-8'))
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed')
        
        # Check that teachers were created
        teacher_count = Teacher.objects.count()
        self.assertTrue(teacher_count > initial_count)
        self.assertEqual(teacher_count, 4)  # We expect 4 teachers from the test file
        
        # Check a specific teacher was created correctly
        try:
            teacher = Teacher.objects.get(id='T001')
            self.assertEqual(teacher.name, 'Sarah Smith')
        except Teacher.DoesNotExist:
            self.fail("Teacher T001 was not created")
    
    def test_room_upload(self):
        """Test uploading room CSV data"""
        # Check initial count
        initial_count = Room.objects.count()
        
        # Prepare the CSV file
        test_file_path = self.get_test_file_path('rooms_test.csv')
        csv_file = self.create_uploaded_file(test_file_path)
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'rooms', 'csv_file': csv_file},
            follow=True
        )
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed')
        self.assertContains(response, 'rooms')
        self.assertTrue(Room.objects.count() > initial_count)
        
        # Check a specific room was created correctly
        room = Room.objects.get(id='R001')
        self.assertEqual(room.number, '101')
        self.assertEqual(room.capacity, 30)
    
    def test_period_upload(self):
        """Test uploading period CSV data"""
        # Check initial count
        initial_count = Period.objects.count()
        
        # Prepare the CSV file
        test_file_path = self.get_test_file_path('periods_test.csv')
        csv_file = self.create_uploaded_file(test_file_path)
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'periods', 'csv_file': csv_file},
            follow=True
        )
        
        # Debug: Print response content
        print("Response content:", response.content.decode('utf-8'))
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed')
        self.assertTrue(Period.objects.count() > initial_count)
        
        # Check a specific period was created correctly
        period = Period.objects.get(id='P001')
        self.assertEqual(period.period_name, 'First Period')
        self.assertEqual(period.days, 'M')
        self.assertEqual(period.slot, '1')
        self.assertEqual(period.start_time.strftime('%H:%M'), '08:00')
        self.assertEqual(period.end_time.strftime('%H:%M'), '08:45')
    
    def test_course_upload(self):
        """Test uploading course CSV data"""
        # Check initial count
        initial_count = Course.objects.count()
        
        # First create a teacher since courses reference teachers
        self.test_teacher_upload()
        
        # Prepare the CSV file
        test_file_path = self.get_test_file_path('courses_test.csv')
        csv_file = self.create_uploaded_file(test_file_path)
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'courses', 'csv_file': csv_file},
            follow=True
        )
        
        # Debug: Print response content
        print("Response content:", response.content.decode('utf-8'))
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed')
        self.assertTrue(Course.objects.count() > initial_count)
        
        # Check a specific course was created correctly
        course = Course.objects.get(id='C001')
        self.assertEqual(course.name, 'Math 6')
        self.assertEqual(course.type, 'core')
        self.assertEqual(course.eligible_teachers, 'T001')
        self.assertEqual(course.grade_level, 6)
        self.assertEqual(course.sections_needed, 2)
        self.assertEqual(course.duration, 'year')
    
    def test_section_upload(self):
        """Test uploading section CSV data"""
        # Clear any existing sections
        Section.objects.all().delete()
        
        # Check initial count
        initial_count = Section.objects.count()
        self.assertEqual(initial_count, 0)  # Ensure we start with 0 sections
        
        # First create prerequisite data
        self.test_teacher_upload()
        self.test_room_upload()
        self.test_period_upload()
        self.test_course_upload()
        
        # Prepare the CSV file
        test_file_path = self.get_test_file_path('sections_test.csv')
        csv_file = self.create_uploaded_file(test_file_path)
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'sections', 'csv_file': csv_file},
            follow=True
        )
        
        # Debug: Print response content
        print("Response content:", response.content.decode('utf-8'))
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed')
        
        # Check that sections were created
        section_count = Section.objects.count()
        self.assertTrue(section_count > initial_count)
        
        # Check a specific section was created correctly
        try:
            section = Section.objects.get(course__id='C001', section_number='1')
            self.assertEqual(section.teacher.id, 'T001')
            self.assertEqual(section.period.id, 'P001')
            self.assertEqual(section.room.id, 'R001')
        except Section.DoesNotExist:
            self.fail("Section for course C001, section 1 was not created")
    
    def test_invalid_csv_format(self):
        """Test uploading a CSV with incorrect format"""
        # Create an invalid CSV file
        content = b'invalid,format\nthis,will,fail'
        csv_file = SimpleUploadedFile('invalid.csv', content, content_type='text/csv')
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'students', 'csv_file': csv_file},
            follow=True
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CSV file missing required headers') 