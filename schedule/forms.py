from django import forms
from .models import Student
from schedule.models import Course, Period

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