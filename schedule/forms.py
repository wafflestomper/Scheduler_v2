from django import forms

class CSVUploadForm(forms.Form):
    DATA_TYPES = [
        ('students', 'Students'),
        ('teachers', 'Teachers'),
        ('rooms', 'Rooms'),
        ('courses', 'Courses'),
        ('periods', 'Periods'),
    ]
    
    data_type = forms.ChoiceField(choices=DATA_TYPES)
    csv_file = forms.FileField(
        label='Select a CSV file',
        help_text='File must be a valid CSV with appropriate headers'
    ) 