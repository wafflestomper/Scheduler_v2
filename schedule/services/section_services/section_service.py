from django.db.models import Count, Q
from ...models import Section, Course, Teacher, Room, Period, Student


class SectionService:
    """Service class for managing section operations."""
    
    @staticmethod
    def get_all_sections_by_course():
        """Get all sections organized by course."""
        # Get all sections with related data
        sections = Section.objects.select_related('course', 'teacher', 'period', 'room').annotate(
            students_count=Count('students')
        )
        
        # Organize sections by course
        sections_by_course = {}
        for section in sections:
            course_id = section.course.id
            course_name = section.course.name
            
            if course_id not in sections_by_course:
                sections_by_course[course_id] = {
                    'course_name': course_name,
                    'sections': []
                }
            
            # Calculate max_size display value
            max_size = section.max_size if section.max_size is not None else "Unlimited"
            
            # Add section to the course group
            sections_by_course[course_id]['sections'].append({
                'id': section.id,
                'section_number': section.section_number,
                'teacher': section.teacher.name if section.teacher else "Unassigned",
                'period': section.period,
                'room': section.room,
                'when': section.get_when_display(),
                'students_count': section.students_count,
                'max_size': max_size,
                'exact_size': section.exact_size
            })
        
        # Sort sections by section number within each course
        for course_id in sections_by_course:
            sections_by_course[course_id]['sections'].sort(key=lambda s: s['section_number'])
            
        return {
            'sections_by_course': sections_by_course,
            'total_sections': sections.count()
        }
    
    @staticmethod
    def get_section_by_id(section_id):
        """Get a section by its ID with all related data."""
        return Section.objects.select_related('course', 'teacher', 'period', 'room').get(pk=section_id)
    
    @staticmethod
    def update_section(section_id, data):
        """Update a section with the provided data."""
        section = SectionService.get_section_by_id(section_id)
        
        # Process teacher
        teacher_id = data.get('teacher_id')
        teacher = Teacher.objects.get(pk=teacher_id) if teacher_id else None
        
        # Process room
        room_id = data.get('room_id')
        room = Room.objects.get(pk=room_id) if room_id else None
        
        # Process period
        period_id = data.get('period_id')
        period = Period.objects.get(pk=period_id) if period_id else None
        
        # Process max_size
        max_size = data.get('max_size')
        if max_size:
            max_size = int(max_size)
            if max_size <= 0:
                raise ValueError("Max size must be a positive integer")
        else:
            max_size = None
        
        # Process exact_size
        exact_size = data.get('exact_size')
        if exact_size:
            exact_size = int(exact_size)
            if exact_size <= 0:
                raise ValueError("Exact size must be a positive integer")
        else:
            exact_size = None
        
        # Update section fields
        section.teacher = teacher
        section.room = room
        section.period = period
        section.max_size = max_size
        section.exact_size = exact_size
        
        section.save()
        return section
    
    @staticmethod
    def create_section(data):
        """Create a new section with the provided data."""
        # Process course
        course_id = data.get('course')
        course = Course.objects.get(pk=course_id)
        
        # Process teacher
        teacher_id = data.get('teacher')
        teacher = Teacher.objects.get(pk=teacher_id) if teacher_id else None
        
        # Process room
        room_id = data.get('room')
        room = Room.objects.get(pk=room_id) if room_id else None
        
        # Process period
        period_id = data.get('period')
        period = Period.objects.get(pk=period_id) if period_id else None
        
        # Process section number
        section_number = data.get('section_number', 1)
        
        # Process max_size
        max_size = data.get('max_size')
        if max_size:
            max_size = int(max_size)
            if max_size <= 0:
                raise ValueError("Max size must be a positive integer")
        
        # Process exact_size
        exact_size = data.get('exact_size')
        if exact_size:
            exact_size = int(exact_size)
            if exact_size <= 0:
                raise ValueError("Exact size must be a positive integer")
        
        # Process when field
        when = data.get('when', 'year')
        
        # Generate section ID
        section_id = f"{course_id}-{section_number}"
        
        # Create section
        section = Section.objects.create(
            id=section_id,
            course=course,
            section_number=int(section_number),
            teacher=teacher,
            room=room,
            period=period,
            max_size=max_size,
            exact_size=exact_size,
            when=when
        )
        
        return section
    
    @staticmethod
    def delete_section(section_id):
        """Delete a section by its ID."""
        section = SectionService.get_section_by_id(section_id)
        section.delete()
        return True
    
    @staticmethod
    def get_section_roster(section_id):
        """Get the roster of students for a section."""
        section = SectionService.get_section_by_id(section_id)
        students = section.students.all().order_by('name')
        
        return {
            'section': section,
            'students': students,
            'student_count': students.count()
        } 