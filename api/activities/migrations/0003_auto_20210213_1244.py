# Generated by Django 3.0.3 on 2021-02-13 11:44

from django.db import migrations, models
import django.db.models.deletion
import djmoney.models.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0010_auto_20210213_1244'),
        ('activities', '0002_auto_20210207_1653'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='type',
            field=models.CharField(choices=[('OF', 'Offer order'), ('CT', 'Change delivery time order'), ('IA', 'Increase amount order'), ('DE', 'Delivery order'), ('RE', 'Revision order'), ('CA', 'Delivery order'), ('MR', 'Money received')], max_length=2),
        ),
        migrations.CreateModel(
            name='MoneyReceivedActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Date time on which the object was created.', verbose_name='created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Date time on which the object was last modified.', verbose_name='modified at')),
                ('amount_currency', djmoney.models.fields.CurrencyField(choices=[('EUR', 'Euro'), ('USD', 'US Dollar')], default='USD', editable=False, max_length=3)),
                ('amount', djmoney.models.fields.MoneyField(blank=True, decimal_places=2, default_currency='USD', max_digits=14, null=True)),
                ('activity', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity')),
                ('offer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.Offer')),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
    ]