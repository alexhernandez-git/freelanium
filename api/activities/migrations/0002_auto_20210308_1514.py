# Generated by Django 3.0.3 on 2021-03-08 14:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0001_initial'),
        ('activities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='revisionactivity',
            name='revision',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.Revision'),
        ),
        migrations.AddField(
            model_name='offeractivity',
            name='activity',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity'),
        ),
        migrations.AddField(
            model_name='offeractivity',
            name='offer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.Offer'),
        ),
        migrations.AddField(
            model_name='increaseamountactivity',
            name='activity',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity'),
        ),
        migrations.AddField(
            model_name='increaseamountactivity',
            name='increase_amount',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.IncreaseAmount'),
        ),
        migrations.AddField(
            model_name='deliveryactivity',
            name='activity',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity'),
        ),
        migrations.AddField(
            model_name='deliveryactivity',
            name='delivery',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='orders.Delivery'),
        ),
        migrations.AddField(
            model_name='changedeliverytimeactivity',
            name='activity',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity'),
        ),
        migrations.AddField(
            model_name='changedeliverytimeactivity',
            name='change_delivery_time',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.ChangeDeliveryTime'),
        ),
        migrations.AddField(
            model_name='cancelorderactivity',
            name='activity',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity'),
        ),
        migrations.AddField(
            model_name='cancelorderactivity',
            name='cancel_order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.CancelOrder'),
        ),
        migrations.AddField(
            model_name='activity',
            name='order',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='orders.Order'),
        ),
    ]