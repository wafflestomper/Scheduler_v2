# Generated by Django 4.2.20 on 2025-03-15 17:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0007_period_period_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='period',
            name='day',
        ),
        migrations.AddField(
            model_name='period',
            name='days',
            field=models.TextField(default='M', help_text="Format: 'M|T|W' for Monday, Tuesday, Wednesday"),
        ),
    ]
