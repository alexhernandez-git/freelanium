# Generated by Django 3.0.3 on 2021-02-24 12:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0010_auto_20210223_1822'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='revision',
            name='issued_by',
        ),
    ]
