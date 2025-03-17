# Scheduling Algorithm Cleanup Plan

## Overview
This document outlines the strategy for removing the existing scheduling algorithms from the School Scheduler application to prepare for implementing new ones that better meet our requirements.

## Current Algorithm Structure

### Main Scheduling Components
1. **schedule/views/schedule_generation_views.py** (473 lines)
   - Contains the main `generate_schedules()` function
   - Includes helper functions for creating core and elective sections
   - Handles student assignment to sections

2. **Specialized Algorithm Modules**
   - `schedule/utils/three_group_elective_algorithm.py` (612 lines)
   - `schedule/utils/two_group_elective_algorithm.py` (502 lines)
   - `schedule/utils/language_core_algorithm.py` (320 lines)
   - `schedule/utils/art_music_ww_algorithm.py` (346 lines)
   - `schedule/utils/balance_assignment.py` (541 lines)
   - `schedule/utils/trimester_course_utils.py` (582 lines)

## Cleanup Approach

### Phase 1: Preserve Current Functionality (Before Deletion)
1. Create a git branch specifically for algorithm cleanup (`git checkout -b algorithm-cleanup`)
2. Create backup copies of all algorithm files in a `backup_algorithms` folder
3. Document algorithm interfaces and dependencies for future reference

### Phase 2: Identify and Remove Algorithm Code
1. **Remove Specialized Algorithm Modules**
   - Move the files to the backup folder and delete from the main codebase:
     - `three_group_elective_algorithm.py`
     - `two_group_elective_algorithm.py`
     - `language_core_algorithm.py`
     - `art_music_ww_algorithm.py`
     - `balance_assignment.py`
     - `trimester_course_utils.py`

2. **Simplify Main Schedule Generation**
   - Replace the complex `generate_schedules()` function in `schedule_generation_views.py` with a simple placeholder
   - Keep all view functions intact but remove algorithm logic
   - Ensure the UI still works without errors (even if scheduling doesn't actually happen)

3. **Update Imports and References**
   - Update any imports to removed modules
   - Add placeholder functions where necessary to prevent errors

### Phase 3: Clean View Code
1. Simplify the schedule generation views to only handle UI concerns
2. Create clear interfaces for future algorithm implementations
3. Document the intended structure for the new algorithms

## New Algorithm Design Considerations

### Proposed Structure
1. **Clean Separation of Concerns**
   - Algorithms should be independent of view code
   - Each algorithm should have a clear interface

2. **Modular Design**
   - Break scheduling into smaller independent steps:
     - Section creation
     - Teacher assignment
     - Room assignment
     - Student enrollment

3. **Configurability**
   - Algorithms should be configurable via settings/parameters
   - Should support different scheduling strategies

4. **Testability**
   - Each algorithm should be independently testable
   - Include clear validation of results

## Implementation Timeline
1. Complete cleanup phase: 1-2 days
2. Design new algorithm interfaces: 2-3 days
3. Implement core scheduling algorithms: 1-2 weeks
4. Testing and refinement: 1 week 