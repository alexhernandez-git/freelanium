from api.utils.models import CModel
from django.db import models


class PlanSubscription(CModel):
    # Login Status

    subscription_id = models.CharField(max_length=100, blank=True, null=True)
    product_id = models.CharField(max_length=100, blank=True, null=True)
    to_be_cancelled = models.BooleanField(null=False, blank=False, default=False)
    cancelled = models.BooleanField(null=False, blank=False, default=False)
    payment_issue = models.BooleanField(null=False, blank=False, default=False)
    current_period_end = models.IntegerField(blank=True, default=0)
    plan = models.ForeignKey("plans.Plan", on_delete=models.SET_NULL, null=True, blank=True)
    plan_unit_amount = models.FloatField(null=True, blank=True)
    plan_currency = models.CharField(max_length=3, blank=True, null=True)
    plan_price_label = models.CharField(max_length=100, blank=True, null=True)
