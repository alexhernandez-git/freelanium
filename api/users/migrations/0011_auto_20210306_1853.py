# Generated by Django 3.0.3 on 2021-03-06 17:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_auto_20210306_1716'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='paypal_account_id',
            new_name='paypal_email',
        ),
    ]
