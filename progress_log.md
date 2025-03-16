# School Scheduler App - Progress Log

## 2023-03-15 - Initial Setup and Implementation

- Created git repository for version control
- Set up Django project structure with schedule app
- Created database models:
  - Teacher
  - Room
  - Student
  - Course
  - Period
  - Section
- Implemented CSV upload functionality for all entity types
- Built scheduling algorithm for generating student schedules
- Created UI templates:
  - Base template with navigation
  - Home page
  - CSV upload page
  - Schedule generation page
  - Master schedule view
  - Student schedule view
  - Section editing page
- Added conflict detection and resolution features
- Implemented schedule export to CSV
- Added sample data CSV files for testing
- Fixed missing import in views.py (redirect function)

## 2023-03-15 - GitHub Repository Setup

- Created remote GitHub repository at https://github.com/wafflestomper/Scheduler_v2.git
- Pushed all code to GitHub for backup and version control
- Added progress tracking log (this file)

## 2023-03-16 - Summary of Completed Work (2023-03-16 12:00)

We've built a Django-based school scheduling application with the following features:

### Data Model
- Created models for Teachers, Rooms, Students, Courses, Periods, and Sections with appropriate relationships between them
- Implemented proper validation and helper methods for accessing and manipulating data

### CSV Import System
- Implemented functionality to bulk-upload data via CSV files for all entity types
- Added validation for imported data to ensure integrity
- Created a user-friendly upload interface with file format guidance

### Scheduling Algorithm
- Developed a constraint-based algorithm that:
  - Creates sections for core courses by grade level
  - Assigns students to appropriate grade-level core classes
  - Creates sections for elective courses
  - Assigns students to electives based on their preferences
  - Handles scheduling constraints (teacher availability, room capacity)

### User Interface
- Built a responsive Bootstrap-based UI with:
  - CSV upload interface with format instructions
  - Master schedule view with conflict detection
  - Student schedule view with filtering options
  - Section editing capability for manual adjustments

### Export Functionality
- Added CSV export for both master and student schedules
- Implemented proper formatting for exported schedules

### Version Control
- Set up Git repository with a full commit history
- Pushed to GitHub at https://github.com/wafflestomper/Scheduler_v2.git
- Created a progress log to document all development milestones

## 2023-03-17 - CSV Format Updates

- Updated CSV import format options for all entity types:
  - **Teachers**: Added first_name, last_name, grade_level (optional), and gender (optional) fields
  - **Students**: Changed to first_name, nickname (optional), last_name, grade_level format
  - **Periods**: Simplified to period_id, start_time, end_time format
  - **Courses**: Updated to course_id, name, teachers (optional), grade_level, duration, sections_needed (optional)
  - **Sections**: Added new CSV import option for sections with course_id, section_number, teacher, period, room, max_size
- Enhanced the CSV upload interface with:
  - Downloadable templates for all entity types
  - Detailed examples with proper data formatting
  - Interactive accordion-style documentation
  - Clear guidance on required and optional fields
- Updated database model for Section to support custom section IDs

## 2023-03-18 - CSV Upload Testing

- Created comprehensive test suite for CSV upload functionality:
  - Added test data files for all entity types (students, teachers, rooms, courses, periods, sections)
  - Implemented test cases to verify successful upload of each entity type
  - Added validation tests to ensure proper error handling for invalid CSV formats
  - Fixed issues with time format handling in period uploads
  - Ensured proper section ID generation and validation
- Enhanced the student name formatting to include nicknames in quotes when available
- Verified that all CSV upload functionality works correctly with the new formats

## 2025-03-15 15:55 - Fixed View Students Feature

Fixed issues with the view students feature:
1. Added the missing `{% load schedule_extras %}` tag to the view_students.html template to load the custom template filter
2. Added 'rest_framework' to INSTALLED_APPS in settings.py
3. Installed Django REST Framework with pip

The view students feature is now working correctly, allowing filtering by grade level and search by name.

## 2025-03-16 12:30 - Implemented Student Detail View and Admin Reports

Enhanced the student management capabilities with the following features:

1. **Student Detail View**:
   - Created a detailed view for individual student information
   - Added student personal data display
   - Implemented schedule display for the student
   - Added navigation breadcrumbs for improved user experience

2. **Student Management**:
   - Implemented edit functionality for student records
   - Added delete capability with confirmation page
   - Created proper form validation for student data

3. **Administrative Reports**:
   - Added a comprehensive reporting dashboard
   - Implemented enrollment statistics by grade level
   - Created course enrollment reporting with class size analytics
   - Added teacher workload reporting
   - Integrated data visualization charts using Chart.js
   - Added sortable tables with DataTables

4. **UI Improvements**:
   - Enhanced navigation with reports link
   - Improved student listing with direct links to student details
   - Added consistent breadcrumb navigation throughout the application
   - Implemented responsive design for all new pages

These enhancements provide administrators with better tools for managing student data and gaining insights into the school's enrollment and scheduling metrics.

## 2025-03-16 15:55 - Enhanced Section Model and Period Descriptions

Improved the flexibility and usability of the scheduling system with the following updates:

1. **Section Model Enhancements**:
   - Made the `room` field optional to allow sections without assigned rooms
   - Made the `max_size` field optional with proper validation
   - Updated CSV processing to handle missing values appropriately
   - Added the `Enrollment` model to properly represent many-to-many relationships between students and sections

2. **Period Description Improvements**:
   - Added a descriptive `period_name` field to the Period model
   - Updated CSV upload template to include the new field
   - Enhanced the display of periods in the UI using the descriptive name when available
   - Updated CSV export to include the new field

3. **CSV Upload Interface Updates**:
   - Updated template documentation to clearly indicate which fields are required vs. optional
   - Fixed template download links to correctly use the proper URL pattern
   - Added example rows showing how to use optional fields

These changes provide more flexibility in the scheduling system, allowing for better descriptions of periods and more scenarios for section creation, such as placeholders without assigned rooms or size limits.

## 2025-03-17 14:30 - Implemented Course Management Interface

Developed comprehensive course management features with the following components:

1. **Course Listing and Management UI**:
   - Created view_courses.html template with a responsive course listing table
   - Implemented sorting by grade level and name for easy navigation
   - Added quick action buttons for edit and delete operations
   - Integrated bootstrap styling for consistent interface

2. **Course Creation Interface**:
   - Implemented create_course.html with a user-friendly form
   - Added validation for all required fields
   - Created a teacher selection modal to easily assign eligible teachers
   - Implemented proper error handling and success messages

3. **Course Editing Capabilities**:
   - Built edit_course.html to allow updating course details
   - Pre-populated form with existing course data
   - Implemented validation and error handling
   - Added clear warning about how changes affect sections

4. **Course Deletion with Safeguards**:
   - Created delete_course_confirm.html with confirmation interface
   - Implemented safeguards to prevent deletion of courses in use by sections
   - Added clear warnings about the irreversible nature of deletions
   - Provided detailed information about the course being deleted

5. **Navigation Integration**:
   - Updated the base.html template to include course management in the dropdown menu
   - Added consistent breadcrumb navigation across all course management pages
   - Ensured proper URL configuration in urls.py

6. **Testing**:
   - Created comprehensive test suite in test_course_views.py
   - Implemented tests for all CRUD operations
   - Added tests for validation and error handling
   - Verified that protections against deleting courses in use work correctly

These features provide administrators with a complete interface for managing courses in the scheduling system, allowing for the easy creation, modification, and removal of courses when needed, while protecting against accidental data loss.

## 2025-03-18 18:35 - Comprehensive Testing and Bug Fixes

Enhanced the application's reliability with extensive testing and bug fixes:

1. **Student Management Testing**:
   - Created test_student_views.py with comprehensive test cases for all student management features
   - Verified functionality of the student list view, detail view, edit, and delete operations
   - Added tests for filtering and search capabilities in the student list view
   - Fixed issues with student deletion and relationship management

2. **Course Management Testing**:
   - Created test_course_views.py with test cases for course CRUD operations
   - Verified that safeguards prevent deletion of courses in use by sections
   - Tested validation of course data during creation and editing
   - Ensured the course listing view properly displays all courses

3. **Admin Reports Testing**:
   - Created test_admin_reports.py to verify reporting functionality
   - Added test cases for enrollment statistics by grade level
   - Tested course enrollment and teacher workload reporting
   - Verified chart data generation and display in templates

4. **ManyToMany Relationship Enhancement**:
   - Properly implemented the Enrollment model to handle student-section relationships
   - Added get_students_list method to the Section model for compatibility with existing code
   - Fixed issues with student removal when deleting student records
   - Updated all dependent code to work with the enhanced relationship model

5. **Bug Fixes**:
   - Fixed AttributeError in admin_reports when sections had no teachers assigned
   - Added safeguards to handle optional relationships throughout the application
   - Updated templates to use the correct field references
   - Fixed error handling in student detail views

These improvements significantly enhance the application's robustness, ensuring all management interfaces handle edge cases properly and providing a solid foundation for future enhancements.

## 2024-03-15 - Code Refactoring for Maintainability

- Refactored views.py into modular view files organized by functionality:
  - Created a views/ package with specialized modules
  - Moved student-related views to student_views.py
  - Moved course-related views to course_views.py
  - Moved teacher-related views to teacher_views.py
  - Moved room-related views to room_views.py
  - Moved period-related views to period_views.py
  - Moved section-related views to section_views.py
  - Moved scheduling generation logic to schedule_generation_views.py
  - Moved import/export functionality to import_export_views.py
  - Created main_views.py for the index/home page
- Updated the main views.py to import and expose all the modular views
- Improved code organization by logically grouping related functionality
- Added proper docstrings to all view functions for better documentation
- Reduced file sizes to improve maintainability, following the < 300 lines guideline

## 2023-05-25 15:30 - Implemented Course Enrollment System

Enhanced the student enrollment management with a new course-based enrollment workflow:

1. **Course Enrollment Model**:
   - Created `CourseEnrollment` model to track student enrollment in courses without immediate section assignment
   - Implemented unique constraints to prevent duplicate enrollments
   - Set up proper relationships between students, courses, and sections

2. **Course Enrollment Interface**:
   - Developed a dedicated enrollment management page accessible via `/enroll-students/`
   - Implemented filtering by grade level and course
   - Added visual indicators for enrolled students
   - Created a responsive, tabular interface showing enrollment statistics
   - Added individual and batch enrollment capabilities
   - Implemented automatic checkbox selection when filters are applied
   - Added checkbox clearing after enrollment to improve user experience

3. **Section Assignment Algorithm**:
   - Added a separate algorithm for assigning enrolled students to sections
   - Implemented capacity-aware section assignment
   - Distributed students across sections based on available capacity
   - Provided detailed feedback on assignment success and failures

4. **API Endpoints**:
   - Created `/api/enroll-student-to-course/` for individual enrollment/unenrollment
   - Implemented `/api/batch-enroll-students/` for bulk enrollment operations
   - Added `/api/assign-students-to-sections/` for running the section assignment algorithm

This new approach separates the course enrollment process from section assignment, allowing administrators to first enroll students in courses and later run an algorithm to place them in appropriate sections. This two-step process provides greater flexibility and enables future enhancements for optimizing section assignments.

## May 3, 2023
Implemented language course scheduling functionality. This new feature allows for specialized scheduling of language courses (SPA6, CHI6, FRE6) for 6th-grade students, ensuring that:
1. Students take each language course in a different trimester
2. All language courses are scheduled in the same period
3. Section enrollments are balanced across available sections

Key components:
- Created `language_course_utils.py` with utility functions:
  - `assign_language_courses`: Assigns language courses to students across different trimesters
  - `get_language_course_conflicts`: Checks for conflicts in language course assignments
  - `balance_language_course_sections`: Balances enrollments across language course sections
- Added view `assign_language_course_sections` for handling assignments
- Created template for language course assignment page
- Added links to the feature in the registration and home pages
- Added missing `registration_home` and `view_student_schedule` functions
- Created student_schedule.html template for viewing individual schedules

The implementation allows administrators to assign language courses manually while enforcing the constraint that each student takes each language course in a different trimester but during the same period across all language courses.

## May 7, 2023
Fixed the section registration AJAX calls that were causing errors with the "Assign All Students" and "Deregister All Section Assignments" buttons. The issue was caused by outdated API endpoint URLs in the JavaScript code that didn't match the current API structure.

Specific changes:
1. Updated the AJAX calls in section_registration.html to use the correct API endpoint
2. Modified the section_registration view to handle the "assign_sections" and "deregister_all_sections" actions
3. Consolidated the API functionality into a single endpoint to improve maintainability
4. Added proper error handling for AJAX requests

This fix ensures that administrators can properly assign students to sections and clear section assignments when needed.

## May 8, 2023
Completed a significant refactoring of the section registration system to improve code organization and maintainability. The main changes include:

1. Reduced file sizes by breaking down large source files into smaller, more focused modules:
   - Moved the LanguageCourseForm class to forms.py
   - Created section_registration_utils.py for utility functions related to section registration
   - Created balance_assignment.py for the section assignment algorithm

2. Improved template organization:
   - Created partial templates for section registration components
   - Split the large section_registration.html template into smaller, reusable components
   - Improved readability and maintainability of HTML templates

3. Simplified views:
   - Reduced the size of the section_registration_views.py file by ~60%
   - Made views more focused with single responsibilities 
   - Improved API endpoint organization

These changes maintain all existing functionality while making the codebase more maintainable and easier to understand. No new features were introduced, but the code structure is now more organized and follows better software engineering practices.

## Next Steps

### UI Improvements
- Add visual schedule display for easier viewing
- Implement drag-and-drop interface for schedule adjustments

### Algorithm Improvements
- Enhance scheduling constraints for better class balance
- Add teacher preference considerations
- Optimize room assignments based on capacity and class size
- Implement student load balancing across sections

### Documentation
- Create user documentation for school administrators
- Add inline code documentation for future maintenance
- Document the CSV format requirements in more detail
- Add setup instructions for new deployments

### Deployment Preparation
- Configure PostgreSQL for production use
- Set up proper environment variables
- Add user authentication for admin functions
- Create a deployment guide

### 2023-05-25 15:30
- Implemented language course groups feature for scheduling related trimester courses
  - Added CourseGroup model to group related language courses (SPA6, CHI6, FRE6)
  - Enhanced section assignment algorithm to respect course group constraints
  - Created course group management interface for creating and editing groups
  - Ensured students enrolled in all courses of a group get assigned to sections with the same period but different trimesters
  - Added admin interface for managing course groups
  - Tested functionality with real language courses and verified correct assignments

## Next Steps

## 2024-03-15 - Implemented 6th Grade Trimester Course Assignment System

Added a specialized system for managing 6th grade trimester courses with the following requirements:
- Three groups of trimester courses:
  - Group 1: WH6 and HW6 (World History pair)
  - Group 2: CTA6 and TAC6 (Computer/Technology pair)
  - Group 3: WW6, Art6, Mus6 (Arts elective options)
- Each student must take one course from each group
- All three courses must be in different trimesters
- All three courses must be in the same period
- Section sizes must be strictly enforced

Implementation includes:
1. New `TrimesterCourseGroup` model to define course relationships
2. Utility functions for assignment, conflict detection, and balancing
3. UI for manual assignment and conflict resolution
4. Initialization script for sample data

This system complements the existing language course rotation system but handles the more complex case of multiple course groups with different options.

## 2024-03-22 - Unified Course Assignment Algorithm

Enhanced the section assignment system with a unified algorithm that handles all course types in a single operation:

1. **Unified Assignment System**:
   - Created a new `unified_assignment` function that seamlessly processes all course types
   - Implemented a phased approach that prioritizes special course types before regular courses
   - Added detailed reporting of assignment statistics for each course type
   - Fixed section configuration issues for trimester courses to ensure consistent period assignments
   - Created diagnostic tools for analyzing and fixing section assignments

2. **Fixed Section Configuration Issues**:
   - Created missing sections for Art6 and Mus6 courses
   - Moved TAC6 and HW6 sections to Period 2 to align with other trimester courses
   - Ensured all trimester courses have sections in all three trimesters in the same period
   - Fixed period conflicts that were preventing proper assignment of students to sections

3. **Testing and Validation**:
   - Implemented comprehensive testing of the unified assignment algorithm
   - Created diagnostic scripts to identify and fix issues with section configurations
   - Verified correct assignment of students to language courses, trimester courses, and regular courses
   - Added detailed analysis reporting for section assignments

This enhancement automates the assignment of all course types - regular, language, and trimester courses - in a single operation when administrators click the "Assign All Students to Sections" button, eliminating the need for separate manual assignments for special course types.

## Next Steps

## 2023-10-22 15:30 - Implemented new language-core algorithm

Created a new algorithm for assigning 6th-grade students to language and core courses. The algorithm follows a more flexible approach:

1. Register students into sections with the most open seats
2. Equalize enrollment across sections
3. If equal, prioritize courses with least total seats
4. Implement backtracking when assignments fail (undo previous assignments and try alternatives)

Changes made:
- Created new `language_core_algorithm.py` with the flexible registration algorithm
- Added API endpoint to run the algorithm in `section_registration_views.py`
- Added UI button and JavaScript to run the algorithm from the section registration page
- Implemented detailed result reporting

This approach should better handle complex scheduling constraints and result in more balanced class sizes.

## 2023-10-22 16:45 - Merged language-core-algorithm branch

Successfully merged the language-core-algorithm branch into main after testing and fixing issues with the implementation:

1. Fixed course type case matching to work with existing database values ('Language' and 'CORE')
2. Updated the algorithm to use section.max_size for capacity calculation
3. Added extensive debug logging to aid in troubleshooting

The algorithm now correctly assigns students to language and core courses using the backtracking approach when needed.

## Next Steps

1. Test the new algorithm with real data and compare results with previous approaches
2. Fine-tune the backtracking parameters if needed
3. Consider extending the algorithm to handle trimester course assignments
4. Add more detailed logging to track algorithm decisions for troubleshooting
5. Consider adding options to customize algorithm parameters through the UI

### 2024-03-16: Two-Group Elective Assignment with Same-Period Constraint

Implemented a more advanced algorithm for handling two course groups simultaneously:

1. Created a new algorithm file `two_group_elective_algorithm.py` that:
   - Assigns students to both Art/Music/WW and Health & Wellness elective groups
   - Ensures both selected courses are in the same period for each student
   - Balances enrollments across sections while respecting max_size and exact_size constraints
   - Uses backtracking to resolve conflicts when students can't be assigned

2. Added a new API endpoint to register students using this algorithm

3. Added a new button "6th Grade Art/Music/WW + Health/Wellness (Same Period)" to the registration actions interface

4. Fixed a UNIQUE constraint error by adding checks to prevent duplicate enrollments:
   - Now checks if a student is already enrolled in a section before attempting to create a new enrollment
   - Filters out students who already have enrollments in both course groups
   - Handles existing enrollments gracefully

This implementation significantly enhances scheduling capabilities by handling the more complex case where students need to be registered for two different course groups while ensuring they're scheduled in the same period.

## Next Steps

### 2024-03-16: Added Section Minimum Size Settings

Implemented a comprehensive system for managing section minimum sizes:

1. Created a new `SectionSettings` model to store minimum size settings for different course types:
   - Core courses (default: 15 students)
   - Elective courses (default: 10 students)
   - Required elective courses (default: 12 students)
   - Language courses (default: 12 students)
   - Added a default maximum size setting (default: 30 students)
   - Added options to enforce minimum sizes and auto-cancel sections below minimums

2. Created a settings administration page:
   - User-friendly interface for adjusting minimum sizes
   - Clear explanations of how settings are used
   - Ability to enable/disable enforcement of minimum sizes

3. Added reporting features:
   - New section in admin reports showing sections below minimum size
   - Statistics on compliance by course type
   - Visual indicators of overall compliance
   - Direct links to adjust settings

4. Added utility functions to support minimum size enforcement in algorithms:
   - `get_section_min_size()` to determine the appropriate minimum for a section
   - `get_sections_below_min_size()` to identify sections that need attention
   - `get_sections_stats()` to generate statistics for reporting

This feature helps administrators ensure that sections have enough students to run effectively and provides tools to identify and address sections that are below the minimum threshold.

## Next Steps

### 2024-03-16: Added Three-Group Elective Assignment Algorithm

Extended the scheduling capabilities with an even more advanced algorithm:

1. Created a new algorithm `three_group_elective_algorithm.py` that:
   - Assigns students to three different elective groups simultaneously:
     - Art/Music/Woodworking group
     - Health & Wellness group
     - Coding & Theatre Arts group
   - Ensures all three assigned sections are in the same period for each student
   - Handles backtracking when conflicts arise
   - Balances section sizes while respecting max_size and exact_size constraints
   - Uses enhanced conflict resolution for this more complex scheduling problem

2. Updated the registration interface with:
   - New UI button in the registration actions panel
   - JavaScript function to handle the three-group assignment
   - Detailed results display showing success/failure counts for all three groups

3. This algorithm demonstrates the scheduler's capacity to handle increasingly complex scheduling constraints while maintaining balanced section sizes.

## Next Steps

### 2024-03-16: Added Student Schedule View

Enhanced the student schedule viewing experience with a new dedicated view:

1. Created a new `student_schedule` view in `student_views.py` that:
   - Shows all classes a student is registered for, organized by period
   - Displays comprehensive information including course, section, teacher, room, and time
   - Highlights unscheduled sections and unassigned courses
   - Provides a summary of the student's schedule status

2. Implemented a new template `student_schedule_view.html` with:
   - Clean, user-friendly layout with responsive design
   - Detailed table of all scheduled classes with period and time information
   - Separate sections for unscheduled classes and courses without assigned sections
   - Schedule summary statistics and quick action buttons

3. Added navigation improvements:
   - Links to the new schedule view from student detail pages
   - Schedule button in the student list for students with enrollments
   - Quick access to related student information

4. Created template tag utilities:
   - Added a `subtract` filter to support schedule statistics calculations

This enhancement provides students, teachers, and administrators with a more comprehensive and user-friendly way to view student schedules, making it easier to identify scheduling issues and ensure students have complete schedules.

## Next Steps 