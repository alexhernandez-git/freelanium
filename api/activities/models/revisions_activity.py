from api.utils.models import CModel
from django.db import models


class RevisionActivity(CModel):

    activity = models.OneToOneField(
        "activities.Activity", on_delete=models.CASCADE, null=True
    )

    revision = models.ForeignKey(
        "orders.Revision", on_delete=models.CASCADE
    )
