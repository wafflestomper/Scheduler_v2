#!/usr/bin/env python
import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

from schedule.models import Student, Course, Section, Period, TrimesterCourseGroup, Enrollment, CourseEnrollment
from django.db import transaction

def fix_trimester_sections():
    """
    Fix the configuration of trimester course sections.
    1. Create missing sections for Art6 and Mus6
    2. Move TAC6 and HW6 sections to Period 2 to match other courses
    """
    print("Fixing trimester course section configuration...")
    
    # Get all trimester course groups
    trimester_groups = TrimesterCourseGroup.objects.all().prefetch_related('courses')
    
    # Get Period 2
    try:
        period_2 = Period.objects.get(id='2')
        print(f"Found Period 2: {period_2.period_name}")
    except Period.DoesNotExist:
        print("Error: Period 2 does not exist")
        return
    
    # Use a transaction to ensure all changes are applied together
    with transaction.atomic():
        # 1. Create missing sections for Art6 and Mus6
        art6 = Course.objects.filter(id='Art6').first()
        if art6:
            print(f"\nCreating sections for {art6.id} - {art6.name}")
            for trimester, section_number in [('t1', 1), ('t2', 2), ('t3', 3)]:
                section_id = f"Art6_S{section_number}"
                section, created = Section.objects.get_or_create(
                    id=section_id,
                    defaults={
                        'course': art6,
                        'section_number': section_number,
                        'period': period_2,
                        'when': trimester
                    }
                )
                if created:
                    print(f"  Created section {section_id} for Period 2, {trimester}")
                else:
                    section.period = period_2
                    section.when = trimester
                    section.save()
                    print(f"  Updated section {section_id} to Period 2, {trimester}")
        
        mus6 = Course.objects.filter(id='Mus6').first()
        if mus6:
            print(f"\nCreating sections for {mus6.id} - {mus6.name}")
            for trimester, section_number in [('t1', 1), ('t2', 2), ('t3', 3)]:
                section_id = f"Mus6_S{section_number}"
                section, created = Section.objects.get_or_create(
                    id=section_id,
                    defaults={
                        'course': mus6,
                        'section_number': section_number,
                        'period': period_2,
                        'when': trimester
                    }
                )
                if created:
                    print(f"  Created section {section_id} for Period 2, {trimester}")
                else:
                    section.period = period_2
                    section.when = trimester
                    section.save()
                    print(f"  Updated section {section_id} to Period 2, {trimester}")
        
        # 2. Move TAC6 sections to Period 2
        tac6 = Course.objects.filter(id='TAC6').first()
        if tac6:
            print(f"\nMoving {tac6.id} sections to Period 2")
            for section in Section.objects.filter(course=tac6):
                old_period = section.period.id if section.period else "None"
                section.period = period_2
                section.save()
                print(f"  Moved section {section.id} from Period {old_period} to Period 2")
        
        # 3. Move HW6 sections to Period 2
        hw6 = Course.objects.filter(id='HW6').first()
        if hw6:
            print(f"\nMoving {hw6.id} sections to Period 2")
            for section in Section.objects.filter(course=hw6):
                old_period = section.period.id if section.period else "None"
                section.period = period_2
                section.save()
                print(f"  Moved section {section.id} from Period {old_period} to Period 2")
    
    print("\nSection configuration update complete!")

if __name__ == "__main__":
    fix_trimester_sections() 