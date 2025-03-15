# School Scheduler App

A comprehensive scheduling application for middle schools to manage student schedules, teacher assignments, and room allocations.

## Features

- **CSV Data Import**: Bulk import data for students, teachers, rooms, courses, and periods
- **Automated Scheduling**: Generate conflict-free schedules based on constraints
- **Schedule Management**: View and edit the master schedule and individual student schedules
- **Conflict Detection**: Identify and resolve scheduling conflicts
- **Data Export**: Export schedules as CSV files

## Technical Stack

- **Backend**: Python/Django
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: HTML, CSS (Bootstrap), JavaScript (jQuery)

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd scheduler_v2
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Apply migrations:
   ```
   python manage.py migrate
   ```

5. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

6. Run the development server:
   ```
   python manage.py runserver
   ```

7. Access the application at http://127.0.0.1:8000/

## CSV Format Requirements

### Students CSV
- Required columns: `student_id,name,grade,elective_prefs`
- Example: `S001,John Doe,6,Art|Robotics`

### Teachers CSV
- Required columns: `teacher_id,name,availability,subjects`
- Example: `T001,Ms. Smith,M1-M6,Math|Science`

### Rooms CSV
- Required columns: `room_id,number,capacity,type`
- Example: `R001,101,30,classroom`

### Courses CSV
- Required columns: `course_id,name,type,grade,max_students,teachers`
- Example: `C001,Math,core,6,30,T001|T002`
- Valid course types: `core`, `elective`, `required_elective`

### Periods CSV
- Required columns: `period_id,day,slot,start_time,end_time`
- Example: `P001,M,1,08:00,08:45`
- Valid days: `M` (Monday), `T` (Tuesday), `W` (Wednesday), `TH` (Thursday), `F` (Friday)

## Workflow

1. Upload CSV files with your data (students, teachers, rooms, courses, periods)
2. Generate schedules using the scheduling algorithm
3. Review the master schedule and student schedules
4. Manually adjust schedules if needed to resolve conflicts
5. Export schedules as CSV files 