from api.utils.models import CModel
from django.db import models

from djmoney.models.fields import MoneyField


class Order(CModel):

    buyer = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="buyer_order")
    seller = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="seller_order")
    title = models.CharField(max_length=256)
    description = models.TextField(max_length=1000)
    unit_amount = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')

    first_payment = MoneyField(max_digits=14, decimal_places=2, default_currency='USD', null=True, blank=True)
    payment_at_delivery = MoneyField(max_digits=14, decimal_places=2, default_currency='USD', null=True, blank=True)

    delivery_date = models.DateTimeField(null=True, blank=True)
    delivery_time = models.IntegerField(null=True, blank=True)
    rate_date = models.CharField(max_length=20, null=True, blank=True)

    TWO_PAYMENTS_ORDER = 'TP'
    NORMAL_ORDER = 'NO'
    RECURRENT_ORDER = 'RO'

    TYPE_CHOICES = [
        (NORMAL_ORDER, 'Two payments order'),
        (TWO_PAYMENTS_ORDER, 'Two payments order'),
        (RECURRENT_ORDER, 'Recurrent order'),
    ]

    type = models.CharField(
        max_length=2,
        choices=TYPE_CHOICES,
    )

    YEAR = 'AN'
    MONTH = 'MO'
    INTERVAL_CHOICES = [
        (YEAR, 'Year'),
        (MONTH, 'Month'),
    ]

    interval_subscription = models.CharField(
        max_length=2,
        choices=INTERVAL_CHOICES,
        default=MONTH
    )

    ACTIVE = 'AC'
    DELIVERED = 'DE'
    CANCELLED = 'CA'

    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled'),
    ]

    status = models.CharField(
        max_length=2,
        choices=STATUS_CHOICES,
        default=ACTIVE
    )

    price_id = models.CharField(max_length=100, blank=True, null=True)

    service_fee = MoneyField(max_digits=14, decimal_places=2, default_currency='USD', null=True, blank=True)

    # (Normal order)
    # Total due to seller at end of order
    due_to_seller = MoneyField(max_digits=14, decimal_places=2, default_currency='USD', null=True, blank=True)

    # (Two payments order)
    # Is first payment already paid
    first_payment_paid = models.BooleanField(default=True)

    payment_at_delivery = models.FloatField(null=True, blank=True)
    payment_at_delivery_currency = models.CharField(max_length=3, null=True, blank=True)

    # (Recurrent payments order)
    subscription_id = models.CharField(max_length=100, blank=True, null=True)
    to_be_cancelled = models.BooleanField(null=False, blank=False, default=False)
    cancelled = models.BooleanField(null=False, blank=False, default=False)
    payment_issue = models.BooleanField(null=False, blank=False, default=False)
    current_period_end = models.IntegerField(blank=True, default=0)
