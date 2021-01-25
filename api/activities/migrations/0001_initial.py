# Generated by Django 3.0.3 on 2021-01-24 10:34

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Date time on which the object was created.', verbose_name='created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Date time on which the object was last modified.', verbose_name='modified at')),
                ('type', models.CharField(choices=[('OF', 'Offer order'), ('CT', 'Change delivery time order'), ('IA', 'Increase amount order'), ('DE', 'Delivery order'), ('RE', 'Revision order'), ('CA', 'Delivery order')], max_length=2)),
                ('order', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='orders.Order')),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='RevisionActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Date time on which the object was created.', verbose_name='created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Date time on which the object was last modified.', verbose_name='modified at')),
                ('activity', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity')),
                ('revision', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.Revision')),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OfferActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Date time on which the object was created.', verbose_name='created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Date time on which the object was last modified.', verbose_name='modified at')),
                ('status', models.CharField(choices=[('PE', 'Pendent'), ('AC', 'Accepted'), ('CA', 'Cancelled')], default='PE', max_length=2)),
                ('closed', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
                ('activity', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity')),
                ('offer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.Offer')),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IncreaseAmountActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Date time on which the object was created.', verbose_name='created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Date time on which the object was last modified.', verbose_name='modified at')),
                ('status', models.CharField(choices=[('PE', 'Pendent'), ('AC', 'Accepted'), ('CA', 'Cancelled')], default='PE', max_length=2)),
                ('closed', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
                ('activity', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity')),
                ('increase_amount', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.IncreaseAmount')),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DeliveryActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Date time on which the object was created.', verbose_name='created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Date time on which the object was last modified.', verbose_name='modified at')),
                ('status', models.CharField(choices=[('PE', 'Pendent'), ('AC', 'Accepted'), ('CA', 'Cancelled')], default='PE', max_length=2)),
                ('closed', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
                ('activity', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity')),
                ('increase_amount', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.IncreaseAmount')),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ChangeDeliveryTimeActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Date time on which the object was created.', verbose_name='created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Date time on which the object was last modified.', verbose_name='modified at')),
                ('status', models.CharField(choices=[('PE', 'Pendent'), ('AC', 'Accepted'), ('CA', 'Cancelled')], default='PE', max_length=2)),
                ('closed', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
                ('activity', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity')),
                ('change_delivery_time', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.ChangeDeliveryTime')),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CancelOrderActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Date time on which the object was created.', verbose_name='created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Date time on which the object was last modified.', verbose_name='modified at')),
                ('status', models.CharField(choices=[('PE', 'Pendent'), ('AC', 'Accepted'), ('CA', 'Cancelled')], default='PE', max_length=2)),
                ('closed', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
                ('activity', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity')),
                ('cancel_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.CancelOrder')),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
    ]
