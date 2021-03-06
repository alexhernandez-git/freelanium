# Generated by Django 3.0.3 on 2021-03-28 20:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('notifications', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chats', '0002_auto_20210328_2249'),
        ('activities', '0002_auto_20210328_2249'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationuser',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='notification',
            name='activity',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='activities.Activity'),
        ),
        migrations.AddField(
            model_name='notification',
            name='actor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='notification',
            name='chat',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='chats.Chat'),
        ),
        migrations.AddField(
            model_name='notification',
            name='messages',
            field=models.ManyToManyField(blank=True, related_name='notifications_messages', to='chats.Message'),
        ),
    ]
