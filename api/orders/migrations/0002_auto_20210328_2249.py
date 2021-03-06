# Generated by Django 3.0.3 on 2021-03-28 20:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='buyer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='buyer_order', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='order',
            name='offer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_offer', to='orders.Offer'),
        ),
        migrations.AddField(
            model_name='order',
            name='seller',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='seller_order', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='offer',
            name='buyer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='offer_buyer_order', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='offer',
            name='seller',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offer_seller_order', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='increaseamount',
            name='issued_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='increase_amount_issued_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='increaseamount',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='increase_amount_order', to='orders.Order'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_order', to='orders.Order'),
        ),
        migrations.AddField(
            model_name='changedeliverytime',
            name='issued_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_delivery_time_issued_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='changedeliverytime',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_delivery_time_order', to='orders.Order'),
        ),
        migrations.AddField(
            model_name='cancelorder',
            name='issued_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cancel_order_issued_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='cancelorder',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cancel_order_order', to='orders.Order'),
        ),
    ]
