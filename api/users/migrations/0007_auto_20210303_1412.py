# Generated by Django 3.0.3 on 2021-03-03 13:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20210303_1330'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='earning',
            name='currency',
        ),
        migrations.RemoveField(
            model_name='earning',
            name='rate_date',
        ),
        migrations.RemoveField(
            model_name='earning',
            name='withdrawn_amount',
        ),
    ]