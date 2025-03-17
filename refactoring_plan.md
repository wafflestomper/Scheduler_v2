# Refactoring Plan for School Scheduler

This document outlines potential refactoring targets in the School Scheduler codebase, focusing on files that exceed the 300-line guideline or contain complex logic that could be better organized.

## High-Priority Refactoring Targets

### 1. schedule/utils/three_group_elective_algorithm.py (612 lines)

**Current Issues:**
- File is over twice the recommended size limit
- Contains a single massive function (register_students_to_three_groups) with nested helper functions
- Excessive print statements for debugging
- Logic for organizing sections by period is repeated

**Refactoring Approach:**
- Extract nested helper functions to module-level functions:
  - `get_best_section` → Separate utility function
  - `register_student_to_period` → Separate registration function
  - `undo_registrations` → Standalone backtracking function
- Create a `period_utils.py` to handle organizing sections by period
- Replace print debugging with proper logging
- Consider splitting into two files:
  - `three_group_algorithm_core.py`: Core algorithm functionality
  - `three_group_registration.py`: API functions to use the algorithm

### 2. schedule/views/section_views.py (598 lines)

**Current Issues:**
- File contains too many view functions
- Some functions, like `edit_section` and `view_sections`, are quite long
- Mixes HTTP response handling with business logic
- Duplicated validation code

**Refactoring Approach:**
- Create a new `section_utils.py` for business logic:
  - Extract validation logic for section fields
  - Move section conflict detection to utility functions
- Split into multiple view files:
  - `section_crud_views.py`: Create, update, delete operations
  - `section_report_views.py`: Export, listing, and reporting functions
  - `section_enrollment_views.py`: Student enrollment in sections

### 3. schedule/utils/trimester_course_utils.py (582 lines)

**Current Issues:**
- Large utility file with complex algorithm logic
- Likely contains functions that could be further broken down

**Refactoring Approach:**
- Review for shared logic with other algorithm files
- Extract common functionality to a shared utility module
- Break down larger functions into smaller, more focused functions

### 4. schedule/views/schedule_generation_views.py (473 lines)

**Current Issues:**
- Mixes view logic with complex schedule generation code
- Contains long functions with multiple responsibilities

**Refactoring Approach:**
- Move schedule generation logic to dedicated utility modules
- Leave only the HTTP handling in the view functions
- Consider using class-based views to organize related functionality

### 5. schedule/views/import_export_views.py (411 lines)

**Current Issues:**
- Contains repetitive pattern for processing various entity types
- Long functions for CSV processing

**Refactoring Approach:**
- Create a generic CSV processor class with entity-specific subclasses
- Extract validation logic into separate utility functions
- Move download template functionality to a separate utility module

## Medium-Priority Refactoring Targets

### 1. schedule/views/course_views.py (309 lines)
- Extract common CRUD operations to utility functions
- Consider class-based views for better organization

### 2. schedule/views/enrollment_views.py (446 lines)
- Separate enrollment business logic from view functions
- Create dedicated utility functions for enrollment operations

## General Refactoring Recommendations

1. **Consistent Pattern for CRUD Operations**
   - Create base classes or utilities for common create, read, update, delete operations
   - Apply consistent validation and error handling patterns

2. **Service Layer**
   - Consider implementing a service layer between views and models
   - Service objects would encapsulate business logic and keep views focused on HTTP concerns

3. **Improved Error Handling**
   - Implement consistent error handling patterns
   - Replace inline error messages with constants or configuration

4. **Test Coverage**
   - Ensure refactored code has adequate test coverage
   - Add tests before refactoring when coverage is low

5. **Documentation**
   - Add or improve docstrings for refactored functions
   - Document complex algorithms with clear explanations of their approach

## Implementation Strategy

1. Start with the highest priority files
2. For each file:
   - Write tests to cover existing functionality (if not already covered)
   - Refactor in small, manageable commits
   - Verify functionality after each refactoring step
3. Update documentation to reflect new structure 