from django import forms
from .models import Student

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file to import data. Please ensure the format matches the templates provided.',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    )
    
    entity_type = forms.ChoiceField(
        choices=[('students', 'Students'), ('teachers', 'Teachers'), ('rooms', 'Rooms'), ('courses', 'Courses'), ('periods', 'Periods'), ('sections', 'Sections')],
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