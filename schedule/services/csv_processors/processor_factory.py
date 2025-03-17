"""
Factory for CSV processors
"""
from typing import Dict, Type, List, Optional
from .base_processor import BaseProcessor
from .student_processor import StudentProcessor
from .teacher_processor import TeacherProcessor
from .room_processor import RoomProcessor
from .course_processor import CourseProcessor
from .period_processor import PeriodProcessor
from .section_processor import SectionProcessor


class ProcessorFactory:
    """Factory for creating appropriate CSV processors based on data type"""
    
    # Registry of processors by data type
    _processors: Dict[str, Type[BaseProcessor]] = {
        'students': StudentProcessor,
        'teachers': TeacherProcessor,
        'rooms': RoomProcessor,
        'courses': CourseProcessor,
        'periods': PeriodProcessor,
        'sections': SectionProcessor,
    }
    
    @classmethod
    def get_processor(cls, data_type: str) -> Optional[Type[BaseProcessor]]:
        """Get the appropriate processor for the data type
        
        Args:
            data_type: Type of data to process ('students', 'teachers', etc.)
            
        Returns:
            Processor class for the data type, or None if not found
        """
        return cls._processors.get(data_type)
    
    @classmethod
    def register_processor(cls, data_type: str, processor: Type[BaseProcessor]) -> None:
        """Register a new processor for a data type
        
        Args:
            data_type: Type of data to process
            processor: Processor class to handle the data type
        """
        cls._processors[data_type] = processor
    
    @classmethod
    def get_available_data_types(cls) -> List[str]:
        """Get list of available data types that can be processed
        
        Returns:
            List of data type strings
        """
        return list(cls._processors.keys())
    
    @classmethod
    def get_expected_headers(cls, data_type: str) -> List[str]:
        """Get expected headers for a data type
        
        Args:
            data_type: Type of data
            
        Returns:
            List of expected header strings, or empty list if processor not found
        """
        processor = cls.get_processor(data_type)
        return processor.get_expected_headers() if processor else [] 