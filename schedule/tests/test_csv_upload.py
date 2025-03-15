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
        self.assertContains(response, 'Successfully processed students data')
        self.assertEqual(Student.objects.count(), initial_count + 4)
        
        # Check a specific student was created correctly
        student = Student.objects.get(id='S001')
        self.assertIn('John', student.name)
        self.assertIn('Doe', student.name)
        self.assertEqual(student.grade_level, 6)
    
    def test_teacher_upload(self):
        """Test uploading teacher CSV data"""
        # Check initial count
        initial_count = Teacher.objects.count()
        
        # Prepare the CSV file
        test_file_path = self.get_test_file_path('teachers_test.csv')
        csv_file = self.create_uploaded_file(test_file_path)
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'teachers', 'csv_file': csv_file},
            follow=True
        )
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed teachers data')
        self.assertEqual(Teacher.objects.count(), initial_count + 4)
        
        # Check a specific teacher was created correctly
        teacher = Teacher.objects.get(id='T001')
        self.assertIn('Sarah', teacher.name)
        self.assertIn('Smith', teacher.name)
        self.assertEqual(teacher.availability, 'M1-M6')
        self.assertEqual(teacher.subjects, 'Math|Science')
    
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
        self.assertContains(response, 'Successfully processed rooms data')
        self.assertEqual(Room.objects.count(), initial_count + 4)
        
        # Check a specific room was created correctly
        room = Room.objects.get(id='R001')
        self.assertEqual(room.number, '101')
        self.assertEqual(room.capacity, 30)
        self.assertEqual(room.type, 'classroom')
    
    def test_period_upload(self):
        """Test uploading period CSV data"""
        # Check initial count
        initial_count = Period.objects.count()
        
        # Create the CSV content directly
        csv_content = "period_id,start_time,end_time\n"
        csv_content += "P001,08:00,08:45\n"
        csv_content += "P002,08:50,09:35\n"
        csv_content += "P003,09:40,10:25\n"
        csv_content += "P004,10:30,11:15"
        
        # Create the file
        csv_file = SimpleUploadedFile("periods_test.csv", csv_content.encode('utf-8'), content_type='text/csv')
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'periods', 'csv_file': csv_file},
            follow=True
        )
        
        # Debug: Print response content
        print("Response content:", response.content.decode())
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed periods data')
        self.assertEqual(Period.objects.count(), initial_count + 4)
        
        # Check a specific period was created correctly
        period = Period.objects.get(id='P001')
        self.assertEqual(period.start_time.strftime('%H:%M'), '08:00')
        self.assertEqual(period.end_time.strftime('%H:%M'), '08:45')
    
    def test_course_upload(self):
        """Test uploading course CSV data"""
        # Check initial count
        initial_count = Course.objects.count()
        
        # Prepare the CSV file
        test_file_path = self.get_test_file_path('courses_test.csv')
        csv_file = self.create_uploaded_file(test_file_path)
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'courses', 'csv_file': csv_file},
            follow=True
        )
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed courses data')
        self.assertEqual(Course.objects.count(), initial_count + 4)
        
        # Check a specific course was created correctly
        course = Course.objects.get(id='C001')
        self.assertEqual(course.name, 'Math 6')
        self.assertEqual(course.grade_level, 6)
        self.assertEqual(course.eligible_teachers, 'T001')
    
    def test_section_upload(self):
        """Test uploading section CSV data"""
        # First we need to create the referenced entities
        self.test_teacher_upload()
        self.test_room_upload()
        self.test_period_upload()
        self.test_course_upload()
        
        # Check initial count
        initial_count = Section.objects.count()
        
        # Create the CSV content directly
        csv_content = "course_id,section_number,teacher,period,room,max_size\n"
        csv_content += "C001,1,T001,P001,R001,30\n"
        csv_content += "C001,2,T001,P002,R002,25\n"
        csv_content += "C002,1,T002,P003,R001,30\n"
        csv_content += "C003,1,T001,P004,R003,20"
        
        # Create the file
        csv_file = SimpleUploadedFile("sections_test.csv", csv_content.encode('utf-8'), content_type='text/csv')
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'sections', 'csv_file': csv_file},
            follow=True
        )
        
        # Debug: Print response content if it fails
        if 'Successfully processed sections data' not in response.content.decode():
            print("Response content:", response.content.decode())
        
        # Assert response and database state
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully processed sections data')
        
        # We expect 4 sections to be created
        self.assertEqual(Section.objects.count(), initial_count + 4)
        
        # Check a specific section was created correctly
        section_id = 'C001_S1'
        section = Section.objects.get(id=section_id)
        self.assertEqual(section.course.id, 'C001')
        self.assertEqual(section.teacher.id, 'T001')
        self.assertEqual(section.period.id, 'P001')
        self.assertEqual(section.room.id, 'R001')
    
    def test_invalid_csv_format(self):
        """Test uploading a CSV with incorrect format"""
        # Create an invalid CSV file
        invalid_csv = SimpleUploadedFile(
            "invalid.csv", 
            b"wrong,header,format\n1,2,3", 
            content_type="text/csv"
        )
        
        # Submit the form
        response = self.client.post(
            reverse('csv_upload'),
            {'data_type': 'students', 'csv_file': invalid_csv},
            follow=True
        )
        
        # Check that we get an error response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error processing CSV') 