from django.test import TestCase, Client
from django.urls import reverse
from ..models import Course, Teacher, Room, Period, Section
from ..services.section_services.section_service import SectionService
from ..services.section_services.conflict_service import ConflictService


class SectionViewsTest(TestCase):
    def setUp(self):
        # Create test data
        self.client = Client()
        
        # Create a course
        self.course = Course.objects.create(
            id="MATH101",
            name="Mathematics 101",
            type="core",
            grade_level=9,
            sections_needed=1
        )
        
        # Create a teacher
        self.teacher = Teacher.objects.create(
            id="T1",
            name="John Smith",
            availability="M1-M6,T1-T6",
            subjects="Math"
        )
        
        # Create a room
        self.room = Room.objects.create(
            id="R101",
            number="101",
            capacity=30,
            type="classroom"
        )
        
        # Create a period
        self.period = Period.objects.create(
            id="P1",
            period_name="Period 1",
            days="M|T|W|TH|F",
            slot="1",
            start_time="08:00",
            end_time="09:00"
        )
        
        # Create a section
        self.section = Section.objects.create(
            id="MATH101_S1",
            course=self.course,
            section_number=1,
            teacher=self.teacher,
            room=self.room,
            period=self.period,
            max_size=30
        )
    
    def test_view_sections(self):
        """Test that the sections view displays correctly."""
        response = self.client.get(reverse('view_sections'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mathematics 101")
        self.assertContains(response, "John Smith")
    
    def test_edit_section(self):
        """Test editing a section."""
        # Create another teacher for the edit
        new_teacher = Teacher.objects.create(
            id="T2",
            name="Jane Doe",
            availability="M1-M6,T1-T6",
            subjects="Math"
        )
        
        # Submit edit form
        response = self.client.post(
            reverse('edit_section', args=[self.section.id]),
            {
                'teacher_id': new_teacher.id,
                'room_id': self.room.id,
                'period_id': self.period.id,
                'max_size': 25,
                'exact_size': 20
            }
        )
        
        # Check redirect and that the section was updated
        self.assertRedirects(response, reverse('view_sections'))
        
        # Refresh section from DB
        self.section.refresh_from_db()
        self.assertEqual(self.section.teacher.id, "T2")
        self.assertEqual(self.section.max_size, 25)
        self.assertEqual(self.section.exact_size, 20)
    
    def test_section_service(self):
        """Test SectionService methods."""
        # Test get_all_sections_by_course
        result = SectionService.get_all_sections_by_course()
        sections_by_course = result['sections_by_course']
        self.assertIn(self.course.id, sections_by_course)
        self.assertEqual(len(sections_by_course[self.course.id]['sections']), 1)
        
        # Test get_section_by_id
        section = SectionService.get_section_by_id(self.section.id)
        self.assertEqual(section.id, self.section.id)
        
        # Test create section
        data = {
            'course': self.course.id,
            'teacher': self.teacher.id,
            'room': self.room.id,
            'period': self.period.id,
            'section_number': 2,
            'max_size': 25,
            'exact_size': 20,
            'when': 'year'
        }
        new_section = SectionService.create_section(data)
        self.assertEqual(new_section.id, f"{self.course.id}-2")
        self.assertEqual(new_section.max_size, 25)
    
    def test_conflict_service(self):
        """Test ConflictService methods."""
        # Create a conflicting section (same teacher, same period)
        course2 = Course.objects.create(
            id="ENG101",
            name="English 101",
            type="core",
            grade_level=9,
            sections_needed=1
        )
        
        conflict_section = Section.objects.create(
            id="ENG101_S1",
            course=course2,
            section_number=1,
            teacher=self.teacher,  # Same teacher
            room=Room.objects.create(
                id="R102", 
                number="102", 
                capacity=25,
                type="classroom"
            ),
            period=self.period,  # Same period
            max_size=25
        )
        
        # Test finding conflicts
        conflicts = ConflictService.find_all_conflicts()
        self.assertTrue(conflicts)  # Should have at least one conflict
        self.assertEqual(conflicts[0]['type'], 'teacher')  # Should be a teacher conflict
        
        # Test checking conflicts for a specific section
        section_conflicts = ConflictService.check_section_conflicts(self.section)
        self.assertTrue(section_conflicts['has_conflicts'])
        self.assertEqual(section_conflicts['conflicts'][0]['type'], 'teacher') 