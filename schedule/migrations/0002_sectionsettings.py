"""
Create SectionSettings model for storing minimum section sizes by course type.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SectionSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('core_min_size', models.IntegerField(default=15, help_text='Minimum size for core courses')),
                ('elective_min_size', models.IntegerField(default=10, help_text='Minimum size for elective courses')),
                ('required_elective_min_size', models.IntegerField(default=12, help_text='Minimum size for required elective courses')),
                ('language_min_size', models.IntegerField(default=12, help_text='Minimum size for language courses')),
                ('default_max_size', models.IntegerField(default=30, help_text='Default maximum section size if not specified')),
                ('enforce_min_sizes', models.BooleanField(default=True, help_text='Whether algorithms should enforce minimum sizes')),
                ('auto_cancel_below_min', models.BooleanField(default=False, help_text='Automatically mark sections for cancellation if below min size')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Section Settings',
                'verbose_name_plural': 'Section Settings',
            },
        ),
    ] 