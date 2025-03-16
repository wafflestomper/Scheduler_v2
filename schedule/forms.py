from django import forms
from .models import Student, Teacher, Room, Course, Section, Period, SectionSettings

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file to import data. Please ensure the format matches the templates provided.',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    )
    
    data_type = forms.ChoiceField(
        choices=[
            ('courses', 'Courses'),
            ('periods', 'Periods'),
            ('rooms', 'Rooms'),
            ('sections', 'Sections'),
            ('students', 'Students'),
            ('teachers', 'Teachers'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['id', 'name', 'grade_level', 'preferences']
        widgets = {
            'id': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'grade_level': forms.Select(attrs={'class': 'form-select'}, 
                                      choices=[(6, 'Grade 6'), (7, 'Grade 7'), (8, 'Grade 8')]),
            'preferences': forms.TextInput(attrs={'class': 'form-control', 
                                                'placeholder': 'Separate with | (e.g. Art|Robotics)'}),
        }
        help_texts = {
            'preferences': 'Enter course preferences separated by | character',
        }

class LanguageCourseForm(forms.Form):
    """Form for language course assignment"""
    student = forms.CharField(
        widget=forms.Select,
        label="Student"
    )
    courses = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label="Courses"
    )
    preferred_period = forms.CharField(
        widget=forms.Select,
        label="Preferred Period",
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get students who are enrolled in language courses
        self.fields['student'].widget.choices = [
            (s.id, s.name) for s in Student.objects.filter(
                course_enrollments__course__type='language'
            ).distinct().order_by('name')
        ]
        
        # Get language courses
        self.fields['courses'].choices = [
            (c.id, f"{c.name} - {c.id}") for c in Course.objects.filter(
                type='language'
            ).order_by('grade_level', 'name')
        ]
        
        # Get periods
        self.fields['preferred_period'].widget.choices = [
            ('', '-- No preference --')
        ] + [
            (p.id, str(p)) for p in Period.objects.all().order_by('slot')
        ]

class TrimesterCourseForm(forms.Form):
    """Form for trimester course assignment"""
    student = forms.CharField(
        widget=forms.Select,
        label="Student"
    )
    group_selections = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label="Group Selections",
        required=False
    )
    preferred_period = forms.CharField(
        widget=forms.Select,
        label="Preferred Period",
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get 6th grade students
        self.fields['student'].widget.choices = [
            (s.id, s.name) for s in Student.objects.filter(
                grade_level=6
            ).distinct().order_by('name')
        ]
        
        # Get trimester course groups
        from schedule.models import TrimesterCourseGroup
        groups = TrimesterCourseGroup.objects.all().prefetch_related('courses')
        
        # Format group selection choices
        group_choices = []
        for group in groups:
            courses = ", ".join([c.id for c in group.courses.all()])
            group_choices.append((
                group.id,
                f"{group.name} ({courses})"
            ))
        
        self.fields['group_selections'].choices = group_choices
        
        # Get periods
        self.fields['preferred_period'].widget.choices = [
            ('', '-- No preference --')
        ] + [
            (p.id, str(p)) for p in Period.objects.all().order_by('slot')
        ]

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['id', 'course', 'section_number', 'teacher', 'period', 'room', 'max_size', 'exact_size', 'when']
        widgets = {
            'id': forms.TextInput(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'section_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'teacher': forms.Select(attrs={'class': 'form-control'}),
            'period': forms.Select(attrs={'class': 'form-control'}),
            'room': forms.Select(attrs={'class': 'form-control'}),
            'max_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'exact_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'when': forms.Select(attrs={'class': 'form-control'}),
        }

class SectionSettingsForm(forms.ModelForm):
    """
    Form for the section settings model.
    """
    class Meta:
        model = SectionSettings
        fields = [
            'name', 
            'core_min_size', 'elective_min_size', 'required_elective_min_size', 'language_min_size',
            'default_max_size', 'enforce_min_sizes', 'auto_cancel_below_min'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'core_min_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'elective_min_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'required_elective_min_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'language_min_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'default_max_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'enforce_min_sizes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_cancel_below_min': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'A descriptive name for these settings (e.g., "2024-2025 Academic Year")',
            'core_min_size': 'Minimum number of students for core course sections',
            'elective_min_size': 'Minimum number of students for elective course sections',
            'required_elective_min_size': 'Minimum number of students for required elective course sections',
            'language_min_size': 'Minimum number of students for language course sections',
            'default_max_size': 'Default maximum section size when not specified at the section level',
            'enforce_min_sizes': 'Whether scheduling algorithms should consider minimum sizes',
            'auto_cancel_below_min': 'Whether to automatically flag sections below minimum size for review',
        } 