"""Users views."""

# Django
import pdb
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


# Django REST Framework
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status, viewsets, mixins
from api.utils.mixins import AddOrderMixin
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from django.http import HttpResponse

# Permissions
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser

# Models
from api.orders.models import Delivery

# Serializers
from api.orders.serializers import DeliveryModelSerializer

# Filters
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

import os
from api.utils import helpers


class DeliveryViewSet(
    mixins.CreateModelMixin,
    AddOrderMixin,
):
    """User view set.

    Handle sign up, login and account verification.
    """

    queryset = Delivery.objects.all()
    lookup_field = "id"
    serializer_class = DeliveryModelSerializer

    def get_permissions(self):
        """Assign permissions based on action."""
        if self.action in ['retrieve']:
            permissions = []

        else:
            permissions = [IsAuthenticated]
        return [p() for p in permissions]

    def create(self, request, *args, **kwargs):

        serializer = DeliveryModelSerializer(data=request.data,
                                             context={
                                                 'order': self.order,
                                                 'request': request,
                                             })
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
