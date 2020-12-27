"""Users views."""

# Django
import pdb
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


# Django REST Framework
from api.users.models import User, UserLoginActivity
import stripe
import json
import uuid
from api.users.serializers import (
    UserLoginSerializer,
    UserModelSerializer,
    UserSignUpSerializer,
    AccountVerificationSerializer,
    ChangePasswordSerializer,
    ChangeEmailSerializer,
    ValidateChangeEmail,
    ForgetPasswordSerializer,
    ResetPasswordSerializer,
)
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from django.http import HttpResponse
# Permissions
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser
)
from api.users.permissions import IsAccountOwner

# Serializers

# Filters
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend


import os
from api.utils import helpers


class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    """User view set.

    Handle sign up, login and account verification.
    """

    queryset = User.objects.filter(is_active=True, is_client=True)
    serializer_class = UserModelSerializer
    lookup_field = 'id'
    filter_backends = (SearchFilter,  DjangoFilterBackend)
    search_fields = ('first_name', 'last_name')

    def get_permissions(self):
        """Assign permissions based on action."""
        if self.action in ['signup', 'login', 'verify', 'list', 'retrieve', 'stripe_webhook_subscription_cancelled', 'forget_password']:
            permissions = [AllowAny]
        elif self.action in ['update', 'delete', 'partial_update', 'change_password', 'change_email', 'validate_change_email', 'reset_password']:
            permissions = [IsAccountOwner, IsAuthenticated]

        else:
            permissions = []
        return [p() for p in permissions]

    def get_serializer_class(self):
        """Return serializer based on action."""

        if self.action in ['list', 'partial_update', 'retrieve']:
            return UserModelSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        return UserModelSerializer

    @action(detail=False, methods=['post'])
    def signup(self, request):
        """User sign up."""

        # request.data['username'] = request.data['email']

        serializer = UserSignUpSerializer(

            data=request.data,
            context={'request': request})
        serializer.is_valid(raise_exception=True)
        user, token = serializer.save()
        user_serialized = UserModelSerializer(user).data
        data = {
            "user": user_serialized,
            "access_token": token
        }
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """User login."""

        serializer = UserLoginSerializer(
            data=request.data,
            context={'request': request}

        )

        serializer.is_valid(raise_exception=True)
        user, token = serializer.save()

        data = {
            'user': UserModelSerializer(user).data,
            'access_token': token,
        }
        if 'STRIPE_API_KEY' in os.environ:
            stripe.api_key = os.environ['STRIPE_API_KEY']
        else:
            stripe.api_key = 'sk_test_51HCsUHIgGIa3w9CpMgSnYNk7ifsaahLoaD1kSpVHBCMKMueUb06dtKAWYGqhFEDb6zimiLmF8XwtLLeBt2hIvvW200YfRtDlPo'

            stripe_account_id = data['user']['stripe_account_id']
            stripe_customer_id = data['user']['stripe_customer_id']
            if stripe_account_id != None and stripe_account_id != '':
                stripe_dashboard_url = stripe.Account.create_login_link(
                    data.get['user']['stripe_account_id']
                )
                data['user']['stripe_dashboard_url'] = stripe_dashboard_url['url']

            if stripe_customer_id != None and stripe_customer_id != '':
                payment_methods = stripe.PaymentMethod.list(
                    customer=stripe_customer_id,
                    type="card"
                )
                data['user']['payment_methods'] = payment_methods.data
            else:
                data['user']['payment_methods'] = None

        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """User login."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'new_password': request.data['new_password'],
                     'repeat_password': request.data['repeat_password']}
        )

        serializer.is_valid(raise_exception=True)

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def forget_password(self, request):
        """User login."""
        serializer = ForgetPasswordSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def change_email(self, request):
        """Account verification."""

        serializer = ChangeEmailSerializer(
            data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        """Account verification."""
        serializer = ResetPasswordSerializer(
            data=request.data, context={'user': request.user, 'confirm_password': request.data['confirm_password']})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """Account verification."""
        serializer = AccountVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = {'message': 'Cuenta verificada!'}
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def validate_change_email(self, request):
        """Account verification."""
        serializer = ValidateChangeEmail(
            data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = {'message': 'Email cambiado!'}
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def remove_card(self, request, *args, **kwargs):
        """Remove payment method"""
        user = request.user
        if 'STRIPE_API_KEY' in os.environ:
            stripe.api_key = os.environ['STRIPE_API_KEY']
        else:
            stripe.api_key = 'sk_test_51HCsUHIgGIa3w9CpMgSnYNk7ifsaahLoaD1kSpVHBCMKMueUb06dtKAWYGqhFEDb6zimiLmF8XwtLLeBt2hIvvW200YfRtDlPo'

        remove = stripe.PaymentMethod.detach(
            request.data.get('payment_method').get('id'),
        )
        return HttpResponse(status=200)

    @action(detail=False, methods=['post'])
    def stripe_connect(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""
        user = request.user
        user = user
        id = request.data.get("id")

        if user.stripe_account_id == None or user.stripe_account_id == '':
            if 'STRIPE_API_KEY' in os.environ:
                stripe.api_key = os.environ['STRIPE_API_KEY']
            else:
                stripe.api_key = 'sk_test_51HCsUHIgGIa3w9CpMgSnYNk7ifsaahLoaD1kSpVHBCMKMueUb06dtKAWYGqhFEDb6zimiLmF8XwtLLeBt2hIvvW200YfRtDlPo'

            response = stripe.OAuth.token(
                grant_type='authorization_code',
                id=id,
            )
            # Access the connected account id in the response
            connected_account_id = response['stripe_user_id']
            if User.objects.filter(stripe_account_id=connected_account_id).exists():
                return HttpResponse(
                    {'message': 'Esta cuenta de stripe ya esta siendo usada por otro usuario'},
                    status=400)

            stripe.Account.modify(
                connected_account_id,
                settings={
                    'payouts': {
                        'schedule': {
                            'interval': 'monthly',
                            'monthly_anchor': 1
                        }
                    }
                }
            )
            partial = request.method == 'PATCH'
            user.stripe_account_id = connected_account_id
            serializer = UserModelSerializer(
                user,
                data=request.data,
                partial=partial
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            data = UserModelSerializer(user).data
            if user.stripe_account_id != None and user.stripe_account_id != '':
                stripe_dashboard_url = stripe.Account.create_login_link(
                    data.get('user').get('stripe_account_id')
                )
                data['user']['stripe_dashboard_url'] = stripe_dashboard_url['url']

            return Response(data)
        else:
            return HttpResponse(status=400)

    @action(detail=False, methods=['get'])
    def get_user(self, request, *args, **kwargs):
        if request.user.id == None:
            return Response(status=404)

        data = {
            'user': UserModelSerializer(request.user, many=False).data,

        }
        if 'STRIPE_API_KEY' in os.environ:
            stripe.api_key = os.environ['STRIPE_API_KEY']
        else:
            stripe.api_key = 'sk_test_51HCsUHIgGIa3w9CpMgSnYNk7ifsaahLoaD1kSpVHBCMKMueUb06dtKAWYGqhFEDb6zimiLmF8XwtLLeBt2hIvvW200YfRtDlPo'

        stripe_account_id = data['user']['stripe_account_id']
        stripe_customer_id = data['user']['stripe_customer_id']
        if stripe_account_id != None and stripe_account_id != '':
            stripe_dashboard_url = stripe.Account.create_login_link(
                data.get['user']['stripe_account_id']
            )
            data['user']['stripe_dashboard_url'] = stripe_dashboard_url['url']

        if stripe_customer_id != None and stripe_customer_id != '':
            payment_methods = stripe.PaymentMethod.list(
                customer=stripe_customer_id,
                type="card"
            )
            data['user']['payment_methods'] = payment_methods.data
        else:
            data['user']['payment_methods'] = None

        return Response(data)
