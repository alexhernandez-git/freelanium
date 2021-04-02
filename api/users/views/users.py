"""Users views."""
# Django
from operator import sub
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


# Django REST Framework
import uuid

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
from stripe.api_resources import plan
from api.users.permissions import IsAccountOwner

# Models
from api.users.models import User, UserLoginActivity, PlanSubscription, Earning, Contact, PlanPayment
from api.plans.models import Plan
from api.orders.models import OrderPayment, Order
from djmoney.money import Money

# Serializers
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
    IsEmailAvailableSerializer,
    IsCouponAvailableSerializer,
    IsUsernameAvailableSerializer,
    InviteUserSerializer,
    StripeConnectSerializer,
    StripeSellerSubscriptionSerializer,
    GetCurrencySerializer,
    SellerChangePaymentMethodSerializer,
    SellerCancelSubscriptionSerializer,
    SellerReactivateSubscriptionSerializer,
    AttachPaymentMethodSerializer,
    AttachPlanPaymentMethodSerializer,
    DetachPaymentMethodSerializer,
    GetUserByJwtSerializer,
    BecomeASellerSerializer,
    PaypalConnectSerializer
)

# Filters
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

# Celery
from api.taskapp.tasks import send_confirmation_email

import os
import stripe
import json

# Utils
from api.utils import helpers

from datetime import timedelta
from django.utils import timezone
import environ
env = environ.Env()


class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  viewsets.GenericViewSet):
    """User view set.

    Handle sign up, login and account verification.
    """

    queryset = User.objects.filter(account_deactivated=False, is_staff=False)
    serializer_class = UserModelSerializer
    lookup_field = 'id'
    filter_backends = (SearchFilter,  DjangoFilterBackend)
    search_fields = ('first_name', 'last_name', 'username')

    def get_permissions(self):
        """Assign permissions based on action."""
        if self.action in [
            'signup',
            'login',
            'verify',
            'stripe_webhooks',
            'stripe_webhooks_invoice_payment_failed',
            'stripe_webhooks_invoice_payment_failed',
                'forget_password']:
            permissions = [AllowAny]
        elif self.action in ['update', 'delete', 'partial_update', 'change_password', 'change_email', 'stripe_connect', 'paypal_connect', 'destroy']:
            permissions = [IsAccountOwner, IsAuthenticated]
        elif self.action in ['list', 'retrieve']:
            permissions = [IsAuthenticated]
        else:
            permissions = []
        return [p() for p in permissions]

    def get_serializer_class(self):
        """Return serializer based on action."""

        if self.action in ['list', 'partial_update', 'retrieve']:
            return UserModelSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        elif self.action == 'invite_user':
            return InviteUserSerializer
        elif self.action == 'get_currency':
            return GetCurrencySerializer
        return UserModelSerializer

    def get_queryset(self):
        if self.action == "list_contacts_available":
            user = self.request.user
            users = Contact.objects.filter(from_user=user).values_list('contact_user__pk')
            users_list = [x[0] for x in users]
            users_list.append(user.pk)
            return User.objects.filter(account_deactivated=False, is_staff=False).exclude(pk__in=users_list)
        return User.objects.filter(account_deactivated=False, is_staff=False)

    # User destroy

    def perform_destroy(self, instance):
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        active_plans_subscription = PlanSubscription.objects.filter(user=instance, cancelled=False)
        for active_plan in active_plans_subscription:
            stripe.Subscription.delete(active_plan.subscription_id)
        active_plans_subscription.update(cancelled=True)

        order_subscriptions = Order.objects.filter(seller=instance, type=Order.RECURRENT_ORDER, cancelled=False)
        for order_subscription in order_subscriptions:
            stripe.Subscription.delete(order_subscription.subscription_id)
        order_subscriptions.update(cancelled=True)
        normal_orders = Order.objects.filter(seller=instance, type=Order.NORMAL_ORDER)
        for normal_order in normal_orders:
            # Return de money to user as credits
            buyer = normal_order.buyer
            buyer.net_income += normal_order.due_to_seller
            Earning.objects.create(
                user=buyer,
                amount=normal_order.due_to_seller,
                type=Earning.REFUND,
                available_for_withdrawn_date=timezone.now() + timedelta(days=14)
            )
            buyer.pending_clearance += normal_order.due_to_seller
            buyer.used_for_purchases -= normal_order.used_credits
            buyer.save()

        instance.account_deactivated = True
        instance.save()

    @action(detail=False, methods=['get'])
    def get_currency(self, request):
        """Check if email passed is correct."""
        serializer = self.get_serializer(data=self.request.data)

        serializer.is_valid(raise_exception=True)
        data = serializer.data

        return Response(data=data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def is_email_available(self, request):
        """Check if email passed is correct."""
        serializer = IsEmailAvailableSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)
        email = serializer.data
        return Response(data=email, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def is_coupon_available(self, request):
        """Check if coupon passed is correct."""
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        serializer = IsCouponAvailableSerializer(
            data=request.data,
            context={'stripe': stripe}
        )

        serializer.is_valid(raise_exception=True)
        coupon = serializer.data
        return Response(data=coupon, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def is_username_available(self, request):
        """Check if email passed is correct."""
        serializer = IsUsernameAvailableSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)
        return Response(data={"message": "This username is available"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def signup_seller(self, request):
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        """User sign up."""
        invitation_token = None
        if 'invitation_token' in request.data:
            invitation_token = request.data['invitation_token']
        coupon = None
        if 'coupon' in request.data and request.data['coupon']:
            coupon = request.data['coupon']

        serializer = UserSignUpSerializer(data=request.data,
                                          context={'request': request, 'seller': True,
                                                   'invitation_token': invitation_token, 'stripe': stripe,
                                                   'coupon': coupon})
        serializer.is_valid(raise_exception=True)
        user, token = serializer.save()
        user_serialized = UserModelSerializer(user).data
        data = {
            "user": user_serialized,
            "access_token": token
        }

        stripe_plan_customer_id = data['user']['stripe_plan_customer_id']
        stripe_customer_id = data['user']['stripe_customer_id']

        # Plan payment methods
        data['user']['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['user']['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def signup_buyer(self, request):
        """User sign up."""

        invitation_token = None
        if 'invitation_token' in request.data:
            invitation_token = request.data['invitation_token']
        serializer = UserSignUpSerializer(
            data=request.data,
            context={'request': request, 'seller': False, 'invitation_token': invitation_token})
        serializer.is_valid(raise_exception=True)
        user, token = serializer.save()
        user_serialized = UserModelSerializer(user).data
        data = {
            "user": user_serialized,
            "access_token": token
        }
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def send_verification_email(self, request):
        """Send the email confirmation."""
        if request.user.id:
            user = request.user
            send_confirmation_email(user)
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)

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
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'

        stripe_plan_customer_id = data['user']['stripe_plan_customer_id']
        stripe_customer_id = data['user']['stripe_customer_id']

        # Plan payment methods
        data['user']['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['user']['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """User login."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
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
    def validate_change_email(self, request):
        """Account verification."""
        serializer = ValidateChangeEmail(
            data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        email = serializer.save()
        data = {'message': 'Email changed!', 'email': email}
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def forget_password(self, request):
        """User login."""
        serializer = ForgetPasswordSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        """Account verification."""
        serializer = ResetPasswordSerializer(
            data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """Account verification."""
        serializer = AccountVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = {'message': 'Verified account!'}
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def remove_card(self, request, *args, **kwargs):
        """Remove payment method"""
        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'

        remove = stripe.PaymentMethod.detach(
            request.data.get('payment_method').get('id'),
        )
        return HttpResponse(status=200)

    @action(detail=False, methods=['post'])
    def stripe_connect(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""
        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = StripeConnectSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def paypal_connect(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""
        user = request.user

        partial = request.method == 'PATCH'
        serializer = PaypalConnectSerializer(
            user,
            data=request.data,
            context={"request": request},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def seller_add_payment_method(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""

        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = StripeSellerSubscriptionSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserModelSerializer(user, many=False).data
        stripe_plan_customer_id = data['stripe_plan_customer_id']
        stripe_customer_id = data['stripe_customer_id']

        # Plan payment methods
        data['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def get_user(self, request, *args, **kwargs):
        if request.user.id == None:
            return Response(status=404)

        data = {
            'user': UserModelSerializer(request.user, many=False).data,

        }
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'

        stripe_plan_customer_id = data['user']['stripe_plan_customer_id']
        stripe_customer_id = data['user']['stripe_customer_id']

        # Plan payment methods
        data['user']['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['user']['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data)

    @action(detail=False, methods=['post'])
    def get_user_by_email_jwt(self, request, *args, **kwargs):
        serializer = GetUserByJwtSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'

        stripe_plan_customer_id = data['user']['stripe_plan_customer_id']
        stripe_customer_id = data['user']['stripe_customer_id']

        # Plan payment methods
        data['user']['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['user']['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data)

    @action(detail=False, methods=['post'])
    def invite_user(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def list_contacts_available(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['patch'])
    def seller_change_payment_method(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""

        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = SellerChangePaymentMethodSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserModelSerializer(user, many=False).data
        stripe_plan_customer_id = data['stripe_plan_customer_id']
        stripe_customer_id = data['stripe_customer_id']

        # Plan payment methods
        data['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def buyer_change_payment_method(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""

        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = SellerChangePaymentMethodSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserModelSerializer(user, many=False).data
        stripe_plan_customer_id = data['stripe_plan_customer_id']
        stripe_customer_id = data['stripe_customer_id']

        # Plan payment methods
        data['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def list_invoices(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""
        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        subscriptions_queryset = PlanSubscription.objects.filter(user=user, cancelled=False)
        if not subscriptions_queryset.exists():
            Response("User have not a plan subscription", status=status.HTTP_404_NOT_FOUND)
        subscription = subscriptions_queryset.first()
        list_data = stripe.Invoice.list(
            customer=user.stripe_plan_customer_id,
            subscription=subscription.subscription_id
        )

        return Response(list_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def seller_cancel_subscription(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""

        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = SellerCancelSubscriptionSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserModelSerializer(user, many=False).data
        stripe_plan_customer_id = data['stripe_plan_customer_id']
        stripe_customer_id = data['stripe_customer_id']

        # Plan payment methods
        data['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def seller_reactivate_subscription(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""

        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = SellerReactivateSubscriptionSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserModelSerializer(user, many=False).data
        stripe_customer_id = data['stripe_customer_id']

        data['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def become_a_seller(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""

        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = BecomeASellerSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserModelSerializer(user, many=False).data
        stripe_customer_id = data['stripe_customer_id']

        data['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def attach_plan_payment_method(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""

        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = AttachPlanPaymentMethodSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserModelSerializer(user, many=False).data

        stripe_plan_customer_id = data['stripe_plan_customer_id']
        stripe_customer_id = data['stripe_customer_id']

        # Plan payment methods
        data['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def attach_payment_method(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""

        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = AttachPaymentMethodSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserModelSerializer(user, many=False).data

        stripe_plan_customer_id = data['stripe_plan_customer_id']
        stripe_customer_id = data['stripe_customer_id']

        # Plan payment methods
        data['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'])
    def detach_payment_method(self, request, *args, **kwargs):
        """Process stripe connect auth flow."""

        user = request.user
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        partial = request.method == 'PATCH'
        serializer = DetachPaymentMethodSerializer(
            user,
            data=request.data,
            context={"request": request, "stripe": stripe},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = UserModelSerializer(user, many=False).data
        stripe_customer_id = data['stripe_customer_id']

        stripe_plan_customer_id = data['stripe_plan_customer_id']
        stripe_customer_id = data['stripe_customer_id']

        # Plan payment methods
        data['plan_payment_methods'] = helpers.get_payment_methods(stripe, stripe_plan_customer_id)
        # Buyer payment methods
        data['payment_methods'] = helpers.get_payment_methods(stripe, stripe_customer_id)

        return Response(data, status=status.HTTP_200_OK)

    # Events that may have to handle:
    # - customer.subscription.trial_will_end - This event notify the subscription trial will end in one day

    @action(detail=False, methods=['post'])
    def stripe_webhook_subscription_deleted(self, request, *args, **kwargs):
        """Process stripe webhook notification for subscription cancellation"""
        payload = request.body
        event = None
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'

        try:
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
            )
        except ValueError as e:
            # Invalid payload
            return HttpResponse(status=400)

        # Handle the event
        if event.type == 'customer.subscription.deleted':
            subscription = event.data.object  # contains a stripe.Subscription

            subscriptions_queryset = PlanSubscription.objects.filter(
                subscription_id=subscription['id'], cancelled=False)

            if subscriptions_queryset.exists():
                plan_subscription = subscriptions_queryset.first()
                user = plan_subscription.user
                plan_subscription.update(cancelled=True)
                user.update(have_active_plan=False)

            # Handle also the recurrent order subscription cancelation
            orders = Order.objects.filter(subscription_id=subscription['id'])

            for order in orders:
                try:
                    stripe.Subscription.delete(subscription['id'])
                except Exception as e:
                    pass
                order.status = Order.CANCELLED
                order.cancelled = True
                order.save()

        return HttpResponse(status=200)

    @action(detail=False, methods=['post'])
    def stripe_webhook_subscription_updated(self, request, *args, **kwargs):
        """Process stripe webhook notification for subscription cancellation"""
        payload = request.body
        event = None
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'

        try:
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
            )
        except ValueError as e:
            # Invalid payload
            return HttpResponse(status=200)

        # Handle the event
        if event.type == 'customer.subscription.updated':
            subscription = event.data.object  # contains a stripe.Subscription
            if subscription['status'] == "active":
                subscriptions_queryset = PlanSubscription.objects.filter(
                    subscription_id=subscription['id'])
                if subscriptions_queryset.exists():
                    plan_subscription = subscriptions_queryset.first()
                    user = plan_subscription.user
                    plan_subscription.update(status="active")
                    user.update(have_active_plan=True, passed_free_trial_once=True, is_free_trial=False)
            if subscription['status'] == "past_due":
                subscriptions_queryset = PlanSubscription.objects.filter(
                    subscription_id=subscription['id'])
                if subscriptions_queryset.exists():
                    plan_subscription = subscriptions_queryset.first()
                    plan_subscription.update(status="past_due")
        return HttpResponse(status=200)

    @action(detail=False, methods=['post'])
    def stripe_webhooks_invoice_payment_succeeded(self, request, *args, **kwargs):
        """Process stripe webhook notification for subscription cancellation"""
        payload = request.body
        event = None
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'

        try:
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
            )
        except ValueError as e:
            # Invalid payload
            return HttpResponse(status=400)
        print(event)
        # Handle the event
        if event.type == 'invoice.payment_succeeded':
            invoice_success = event.data.object
            invoice_id = invoice_success['id']
            charge_id = invoice_success['charge']
            invoice_pdf = invoice_success['invoice_pdf']
            subscription_id = invoice_success['subscription']
            amount_paid = float(invoice_success['amount_paid']) / 100
            currency = invoice_success['currency']
            status = invoice_success['status']

            # Get plan subscription
            plan_subscriptions = PlanSubscription.objects.filter(subscription_id=subscription_id)

            if plan_subscriptions.exists():
                plan_subscription = plan_subscriptions.first()
                plan_user = plan_subscription.user
                PlanPayment.objects.create(
                    user=plan_user,
                    invoice_id=invoice_id,
                    subscription_id=subscription_id,
                    invoice_pdf=invoice_pdf,
                    charge_id=charge_id,
                    amount_paid=amount_paid,
                    currency=currency,
                    status=status,
                )

                if plan_user.free_trial_invoiced:

                    if plan_user.active_month:

                        def create_new_price():
                            price = stripe.Price.create(
                                unit_amount=int(plan_subscription.plan_unit_amount * 100),
                                currency=plan_subscription.plan_currency,
                                product=product_id,
                                recurring={"interval": "month"},
                            )

                            subscription = stripe.Subscription.retrieve(
                                subscription_id)

                            stripe.Subscription.modify(
                                subscription_id,
                                cancel_at_period_end=False,
                                proration_behavior=None,
                                items=[
                                    {
                                        'id': subscription['items']['data'][0]['id'],
                                        "price": price['id']
                                    },
                                ],
                            )

                        product_id = plan_subscription.product_id
                        plan_currency = plan_subscription.plan_currency
                        plans = Plan.objects.filter(stripe_product_id=product_id, currency=plan_currency)
                        if plans.exists():
                            plan = plans.first()
                            if plan.unit_amount != plan_subscription.plan_unit_amount:
                                create_new_price()
                            else:

                                subscription = stripe.Subscription.retrieve(
                                    subscription_id)

                                stripe.Subscription.modify(
                                    subscription_id,
                                    cancel_at_period_end=False,
                                    proration_behavior=None,
                                    items=[
                                        {
                                            'id': subscription['items']['data'][0]['id'],
                                            "price": plan.stripe_price_id
                                        },
                                    ],
                                )

                        # If plan does not exists
                        else:
                            create_new_price()

                        plan_user.active_month = False
                        plan_user.save()
                    else:
                        product_id = plan_subscription.product_id

                        price = stripe.Price.create(
                            unit_amount=0,
                            currency=plan_user.currency,
                            recurring={"interval": "month"},

                            product=product_id
                        )

                        subscription = stripe.Subscription.retrieve(
                            subscription_id)

                        stripe.Subscription.modify(
                            subscription_id,
                            cancel_at_period_end=False,
                            proration_behavior=None,
                            items=[
                                {
                                    'id': subscription['items']['data'][0]['id'],
                                    "price": price['id']
                                },
                            ],
                        )
                else:
                    # enter the free trial invocie
                    plan_user.free_trial_invoiced = True
                    plan_user.save()

                return HttpResponse(status=200)

            orders = Order.objects.filter(subscription_id=subscription_id).exclude(subscription_id=None)

            if not orders.exists():
                return HttpResponse(status=200)

            order = orders.first()
            OrderPayment.objects.create(
                order=order,
                invoice_id=invoice_id,
                invoice_pdf=invoice_pdf,
                charge_id=charge_id,
                amount_paid=amount_paid,
                currency=currency,
                status=status,
            )
            rate_date = order.rate_date
            seller = order.seller
            buyer = order.buyer
            used_credits = order.used_credits

            if used_credits:
                Earning.objects.create(
                    user=buyer,
                    type=Earning.SPENT,
                    amount=used_credits
                )

                # Substract in pending_clearance and available_for_withdrawal the used credits amount
                pending_clearance = buyer.pending_clearance - used_credits

                if pending_clearance < Money(amount=0, currency="USD"):
                    buyer.pending_clearance = Money(amount=0, currency="USD")
                    available_money_payed = abs(pending_clearance)

                    available_for_withdrawal = buyer.available_for_withdrawal - available_money_payed
                    if available_for_withdrawal < Money(amount=0, currency="USD"):
                        available_for_withdrawal = Money(amount=0, currency="USD")
                    buyer.available_for_withdrawal = available_for_withdrawal
                else:
                    buyer.pending_clearance = pending_clearance

                buyer.used_for_purchases += used_credits

                buyer.save()

            order_fee = order.service_fee
            unit_amount_without_fees = order.offer.unit_amount

            new_cost_of_subscription = unit_amount_without_fees + order_fee

            order.unit_amount = new_cost_of_subscription
            order.used_credits = 0
            order.save()

            new_cost_of_subscription, _ = helpers.convert_currency(
                buyer.currency, "USD", new_cost_of_subscription.amount, rate_date)

            switcher = {
                Order.MONTH: "month",
                Order.YEAR: "year"
            }
            interval = switcher.get(order.interval_subscription, None)
            price = stripe.Price.create(
                unit_amount=int(new_cost_of_subscription * 100),
                currency=buyer.currency,
                product=order.product_id,
                recurring={"interval": interval}
            )

            subscription = stripe.Subscription.retrieve(
                subscription_id)

            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False,
                proration_behavior=None,
                items=[
                    {
                        'id': subscription['items']['data'][0]['id'],
                        "price": price['id']
                    },
                ],
            )

            due_to_seller = order.offer.unit_amount

            seller.net_income = seller.net_income + due_to_seller

            Earning.objects.create(
                user=seller,
                amount=due_to_seller,
                available_for_withdrawn_date=timezone.now() + timedelta(days=14)
            )

            seller.pending_clearance += due_to_seller

            seller.save()

            return HttpResponse(status=200)

        else:
            # Unexpected event type
            return HttpResponse(status=200)

    @ action(detail=False, methods=['post'])
    def stripe_webhooks_invoice_payment_failed(self, request, *args, **kwargs):
        """Process stripe webhook notification for subscription cancellation"""
        payload = request.body
        event = None
        if 'STRIPE_API_KEY' in env:
            stripe.api_key = env('STRIPE_API_KEY')
        else:
            stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'

        try:
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
            )
        except ValueError as e:
            # Invalid payload
            return HttpResponse(status=400)
        print(event)
        # Handle the event
        if event.type == 'invoice.payment_failed':
            invoice_failed = event.data.object
            subscription_id = invoice_failed['subscription']

            orders = Order.objects.filter(subscription_id=subscription_id)

            for order in orders:
                try:
                    stripe.Subscription.delete(subscription_id)
                except Exception as e:
                    pass
                order.status = Order.CANCELLED
                order.cancelled = True
                order.payment_issue = True
                order.save()

        return HttpResponse(status=200)


# {
#   "id": "sub_IlnjqhWRBzlgmq",
#   "object": "subscription",
#   "application_fee_percent": None,
#   "billing_cycle_anchor": 1612018313,
#   "billing_thresholds": None,
#   "cancel_at": None,
#   "cancel_at_period_end": False,
#   "canceled_at": 1610808975,
#   "collection_method": "charge_automatically",
#   "created": 1610808713,
#   "current_period_end": 1612018313,
#   "current_period_start": 1610808713,
#   "customer": "cus_IlnhrxdXMms1ao",
#   "days_until_due": None,
#   "default_payment_method": None,
#   "default_source": None,
#   "default_tax_rates": [],
#   "discount": None,
#   "ended_at": 1610808975,
#   "items": {
#     "object": "list",
#     "data": [
#       {
#         "id": "si_Ilnj5Ut5sI4IBp",
#         "object": "subscription_item",
#         "billing_thresholds": None,
#         "created": 1610808713,
#         "metadata": {},
#         "price": {
#           "id": "price_1IAG7VCob7soW4zYt7WFhGOr",
#           "object": "price",
#           "active": True,
#           "billing_scheme": "per_unit",
#           "created": 1610808677,
#           "currency": "eur",
#           "livemode": False,
#           "lookup_key": None,
#           "metadata": {},
#           "nickname": None,
#           "product": "prod_IlnimGxTUwdFZb",
#           "recurring": {
#             "aggregate_usage": None,
#             "interval": "month",
#             "interval_count": 1,
#             "usage_type": "licensed"
#           },
#           "tiers_mode": None,
#           "transform_quantity": None,
#           "type": "recurring",
#           "unit_amount": 999,
#           "unit_amount_decimal": "999"
#         },
#         "quantity": 1,
#         "subscription": "sub_IlnjqhWRBzlgmq",
#         "tax_rates": []
#       }
#     ],
#     "has_more": False,
#     "url": "/v1/subscription_items?subscription=sub_IlnjqhWRBzlgmq"
#   },
#   "latest_invoice": "in_1IAG85Cob7soW4zYJ8uQqSV1",
#   "livemode": False,
#   "metadata": {},
#   "next_pending_invoice_item_invoice": None,
#   "pause_collection": None,
#   "pending_invoice_item_interval": None,
#   "pending_setup_intent": None,
#   "pending_update": None,
#   "schedule": None,
#   "start_date": 1610808713,
#   "status": "canceled",
#   "transfer_data": None,
#   "trial_end": 1612018313,
#   "trial_start": 1610808713
# }
