# Generated by Django 3.0.3 on 2021-03-03 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20210303_1412'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='active_month',
            field=models.BooleanField(default=False),
        ),
    ]