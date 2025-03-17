#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scheduler.settings')
django.setup()

# Now import Django models and services
from schedule.services.section_registration_services.algorithm_service import AlgorithmService

# Run the algorithm for language courses
result = AlgorithmService.balance_section_assignments('SPA6')
print(result)

result = AlgorithmService.balance_section_assignments('CHI6')
print(result)

result = AlgorithmService.balance_section_assignments('FRE6')
print(result)
