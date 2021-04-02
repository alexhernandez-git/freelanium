from api.utils.models import CModel
from django.db import models


class Plan(CModel):

    BASIC = 'BA'
    TYPE_CHOICES = [
        (BASIC, 'Basic'),
    ]
    type = models.CharField(
        max_length=2,
        choices=TYPE_CHOICES,
    )

    unit_amount = models.FloatField(null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True, null=True)
    price_label = models.CharField(max_length=100, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True)
