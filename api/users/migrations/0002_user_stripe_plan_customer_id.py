# Generated by Django 3.0.3 on 2021-02-08 15:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='stripe_plan_customer_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
