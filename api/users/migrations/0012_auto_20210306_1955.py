# Generated by Django 3.0.3 on 2021-03-06 18:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_auto_20210306_1853'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='earning',
            name='transfer_id',
        ),
        migrations.AddField(
            model_name='earning',
            name='batch_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
