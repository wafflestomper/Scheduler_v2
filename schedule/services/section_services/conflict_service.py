from django.db.models import Q
from ...models import Section, Teacher, Room, Student


class ConflictService:
    """Service class for detecting and managing schedule conflicts."""
    
    @staticmethod
    def find_all_conflicts():
        """Find all schedule conflicts in the current schedule."""
        conflicts = []
        
        # Get all sections with a period assigned
        sections = Section.objects.exclude(period__isnull=True).select_related('period', 'course', 'teacher', 'room')
        
        # Add teacher conflicts
        conflicts.extend(ConflictService._find_teacher_conflicts(sections))
        
        # Add room conflicts
        conflicts.extend(ConflictService._find_room_conflicts(sections))
        
        # Add student conflicts
        conflicts.extend(ConflictService._find_student_conflicts(sections))
        
        return conflicts
    
    @staticmethod
    def _find_teacher_conflicts(sections):
        """Find conflicts where the same teacher is assigned to multiple sections in the same period."""
        conflicts = []
        
        # Check for teacher conflicts (same teacher, same period)
        teachers = Teacher.objects.all()
        for teacher in teachers:
            teacher_sections = sections.filter(teacher=teacher)
            periods_with_sections = {}
            
            for section in teacher_sections:
                if not section.period:
                    continue
                    
                period_id = section.period.id
                if period_id in periods_with_sections:
                    # Conflict: Teacher assigned to multiple sections in the same period
                    conflict = {
                        'type': 'teacher',
                        'description': f"Teacher {teacher.name} assigned to multiple sections in period {section.period.period_name}",
                        'sections': [
                            {
                                'id': periods_with_sections[period_id].id,
                                'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                                'period': periods_with_sections[period_id].period.period_name,
                                'room': periods_with_sections[period_id].room.number if periods_with_sections[period_id].room else "Unassigned"
                            },
                            {
                                'id': section.id,
                                'course': section.course.name if section.course else "Unassigned",
                                'period': section.period.period_name,
                                'room': section.room.number if section.room else "Unassigned"
                            }
                        ]
                    }
                    conflicts.append(conflict)
                else:
                    periods_with_sections[period_id] = section
        
        return conflicts
    
    @staticmethod
    def _find_room_conflicts(sections):
        """Find conflicts where the same room is assigned to multiple sections in the same period."""
        conflicts = []
        
        # Check for room conflicts (same room, same period)
        rooms = Room.objects.all()
        for room in rooms:
            room_sections = sections.filter(room=room)
            periods_with_sections = {}
            
            for section in room_sections:
                if not section.period:
                    continue
                    
                period_id = section.period.id
                if period_id in periods_with_sections:
                    # Conflict: Room assigned to multiple sections in the same period
                    conflict = {
                        'type': 'room',
                        'description': f"Room {room.number} assigned to multiple sections in period {section.period.period_name}",
                        'sections': [
                            {
                                'id': periods_with_sections[period_id].id,
                                'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                                'period': periods_with_sections[period_id].period.period_name,
                                'teacher': periods_with_sections[period_id].teacher.name if periods_with_sections[period_id].teacher else "Unassigned"
                            },
                            {
                                'id': section.id,
                                'course': section.course.name if section.course else "Unassigned",
                                'period': section.period.period_name,
                                'teacher': section.teacher.name if section.teacher else "Unassigned"
                            }
                        ]
                    }
                    conflicts.append(conflict)
                else:
                    periods_with_sections[period_id] = section
        
        return conflicts
    
    @staticmethod
    def _find_student_conflicts(sections):
        """Find conflicts where students are assigned to multiple sections in the same period."""
        conflicts = []
        
        # Check for student conflicts (same student, same period)
        # Get all students
        students = Student.objects.prefetch_related('sections')
        
        for student in students:
            student_sections = student.sections.all()
            periods_with_sections = {}
            
            for section in student_sections:
                if not section.period:
                    continue
                    
                period_id = section.period.id
                if period_id in periods_with_sections:
                    # Conflict: Student assigned to multiple sections in the same period
                    conflict = {
                        'type': 'student',
                        'description': f"Student {student.name} assigned to multiple sections in period {section.period.period_name}",
                        'sections': [
                            {
                                'id': periods_with_sections[period_id].id,
                                'course': periods_with_sections[period_id].course.name if periods_with_sections[period_id].course else "Unassigned",
                                'period': periods_with_sections[period_id].period.period_name,
                            },
                            {
                                'id': section.id,
                                'course': section.course.name if section.course else "Unassigned",
                                'period': section.period.period_name,
                            }
                        ],
                        'student': {
                            'id': student.id,
                            'name': student.name
                        }
                    }
                    conflicts.append(conflict)
                else:
                    periods_with_sections[period_id] = section
        
        return conflicts
    
    @staticmethod
    def check_section_conflicts(section):
        """Check for conflicts for a specific section."""
        conflicts = []
        
        # Check for teacher conflicts
        if section.teacher and section.period:
            teacher_conflicts = Section.objects.filter(
                teacher=section.teacher,
                period=section.period
            ).exclude(id=section.id)
            
            if teacher_conflicts.exists():
                for conflict in teacher_conflicts:
                    conflicts.append({
                        'type': 'teacher',
                        'message': f"Teacher {section.teacher.name} is already assigned to {conflict.course.name} section {conflict.section_number} during this period"
                    })
        
        # Check for room conflicts
        if section.room and section.period:
            room_conflicts = Section.objects.filter(
                room=section.room,
                period=section.period
            ).exclude(id=section.id)
            
            if room_conflicts.exists():
                for conflict in room_conflicts:
                    conflicts.append({
                        'type': 'room',
                        'message': f"Room {section.room.number} is already assigned to {conflict.course.name} section {conflict.section_number} during this period"
                    })
        
        # Check for student conflicts
        student_conflicts = []
        if section.period:
            for student in section.students.all():
                other_sections = student.sections.filter(period=section.period).exclude(id=section.id)
                if other_sections.exists():
                    student_conflicts.append({
                        'student': student.name,
                        'conflicts': [f"{s.course.name} section {s.section_number}" for s in other_sections]
                    })
        
        if student_conflicts:
            conflicts.append({
                'type': 'student',
                'message': "Some students have conflicts with this section",
                'details': student_conflicts
            })
        
        return {
            'section_id': section.id,
            'section_name': f"{section.course.name} section {section.section_number}",
            'conflicts': conflicts,
            'has_conflicts': len(conflicts) > 0
        } 