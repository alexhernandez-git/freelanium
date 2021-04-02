"""Plans models admin."""

# Django
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

# Models
from api.plans.models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Plan model admin."""

    list_display = ("price_label", "type", "currency", "stripe_price_id", "stripe_product_id")
