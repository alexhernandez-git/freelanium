# Generated by Django 3.0.3 on 2021-02-19 13:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_order_offer'),
    ]

    operations = [
        migrations.RenameField(
            model_name='delivery',
            old_name='source_files',
            new_name='source_file',
        ),
        migrations.DeleteModel(
            name='Images',
        ),
    ]