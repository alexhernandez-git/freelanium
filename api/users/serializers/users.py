"""Users serializers."""

# Django
from ccy.core.currency import currency
from django.conf import settings
from django.contrib.auth import password_validation, authenticate
from django.core.validators import RegexValidator, validate_email
from django.shortcuts import get_object_or_404
from django.db.models import Sum

# Django REST Framework
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.validators import UniqueValidator

# Models
from api.users.models import User, UserLoginActivity, PlanSubscription, Earning
from api.notifications.models import Notification
from api.plans.models import Plan
from api.activities.models import Activity
from djmoney.models.fields import Money


# Serializers
from .plan_subscriptions import PlanSubscriptionModelSerializer

# Celery
from api.taskapp.tasks import (
    send_confirmation_email,
    send_change_email_email,
    send_reset_password_email,
    send_invitation_email
)


# Utilities
import jwt
import datetime
from django.utils import timezone

from api.utils import helpers
import re
import geoip2.database
import ccy

import environ
env = environ.Env()


class UserModelSerializer(serializers.ModelSerializer):
    """User model serializer."""
    pending_notifications = serializers.SerializerMethodField(read_only=True)
    pending_messages = serializers.SerializerMethodField(read_only=True)
    current_plan_subscription = serializers.SerializerMethodField(read_only=True)
    earned_this_month = serializers.SerializerMethodField(read_only=True)

    class Meta:
        """Meta class."""

        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'about',
            'phone_number',
            'country',
            'is_staff',
            'is_verified',
            'picture',
            'is_seller',
            'seller_view',
            'is_free_trial',
            'passed_free_trial_once',
            'free_trial_expiration',
            'have_active_plan',
            'stripe_plan_customer_id',
            'stripe_customer_id',
            'currency',
            'paypal_email',
            'net_income',
            'withdrawn',
            'used_for_purchases',
            'available_for_withdrawal',
            'pending_clearance',
            'pending_messages',
            'pending_notifications',
            'default_payment_method',
            'plan_default_payment_method',
            'current_plan_subscription',
            'earned_this_month',
        )

        read_only_fields = (
            'id',
        )

    def get_pending_notifications(self, obj):

        return obj.notifications.through.objects.filter(user=obj, is_read=False).exists()

    def get_pending_messages(self, obj):
        return obj.notifications.through.objects.filter(
            user=obj, is_read=False, notification__type__in=[Notification.MESSAGES, Notification.ACTIVITY]).exists()

    def get_current_plan_subscription(self, obj):

        subscriptions_queryset = PlanSubscription.objects.filter(user=obj, cancelled=False)
        if not subscriptions_queryset.exists():
            return None
        plan_subscription = subscriptions_queryset.first()
        return PlanSubscriptionModelSerializer(plan_subscription, many=False).data

    def get_earned_this_month(self, obj):

        today = timezone.now()

        earnings = Earning.objects.filter(
            created__month=today.month, user=obj, type=Earning.ORDER_REVENUE).aggregate(
            Sum('amount'))
        return earnings.get('amount__sum', None)


class GetUserByJwtSerializer(serializers.Serializer):
    user = UserModelSerializer(read_only=True)
    access_token = serializers.CharField(read_only=True)
    token = serializers.CharField()

    def validate_token(self, data):
        """Verifiy token is valid."""
        try:
            payload = jwt.decode(data, settings.SECRET_KEY,
                                 algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise serializers.ValidationError('Verification link has expired')
        except jwt.PyJWTError:
            raise serializers.ValidationError('Invalid token')
        if payload['type'] != 'user_token':
            raise serializers.ValidationError('Invalid token')

        self.context['payload'] = payload

        return data

    def validate(self, data):
        payload = self.context['payload']
        user = User.objects.get(id=payload['user'])
        token, created = Token.objects.get_or_create(
            user=user)
        data['access_token'] = token
        data['user'] = user
        return data


class GetCurrencySerializer(serializers.Serializer):
    currency = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        request = self.context['request']
        current_login_ip = helpers.get_client_ip(request)
        # Remove this line in production
        if env.bool("DEBUG", default=True):
            current_login_ip = "147.161.106.227"
        data['currency'] = helpers.get_currency_api(current_login_ip)
        return data


class UserSignUpSerializer(serializers.Serializer):
    """Useer sign up serializer.

    Handle sign up data validation and user/profile creation.
    """

    email = serializers.CharField(
        validators=[
            UniqueValidator(queryset=User.objects.all())
        ],
        required=False,
    )
    username = serializers.CharField(
        min_length=4,
        max_length=40,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    # Phone number
    phone_regex = RegexValidator(
        regex=r'\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: +999999999. Up to 15 digits allowed."
    )
    phone_number = serializers.CharField(
        validators=[phone_regex], required=False)

    # Password
    password = serializers.CharField(min_length=8, max_length=64)
    password_confirmation = serializers.CharField(min_length=8, max_length=64)

    # Name
    first_name = serializers.CharField(min_length=2, max_length=30)
    last_name = serializers.CharField(min_length=2, max_length=30)

    # Currency for seller subscription
    currency = serializers.CharField(max_length=3, required=False)

    def validate(self, data):
        """Verify passwords match."""
        passwd = data['password']
        passwd_conf = data['password_confirmation']
        if passwd != passwd_conf:
            raise serializers.ValidationError('Las contraseñas no coinciden')
        password_validation.validate_password(passwd)

        # Verifiy token is valid
        if 'invitation_token' in self.context and self.context['invitation_token']:
            invitation_token = self.context['invitation_token']
            try:
                payload = jwt.decode(invitation_token, settings.SECRET_KEY,
                                     algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                raise serializers.ValidationError('Token has expired')
            except jwt.PyJWTError:
                raise serializers.ValidationError('Invalid token')
            if payload['type'] != 'invitation_token':
                raise serializers.ValidationError('Invalid token')
            self.context['payload'] = payload
        if 'coupon' in self.context and self.context['coupon']:
            coupon = self.context['coupon']

            stripe = self.context['stripe']

            try:
                stripe_coupon = stripe.Coupon.retrieve(coupon)
                if not stripe_coupon['valid']:
                    raise serializers.ValidationError({'coupon': 'This coupon is not valid'})

            except:
                raise serializers.ValidationError({'coupon': 'This coupon does not exist'})

        return data

    def create(self, data):
        """Handle user and profile creation."""
        request = self.context['request']
        is_seller = self.context['seller']

        data.pop('password_confirmation')

        # Create the free trial expiration date

        currency, country = helpers.get_currency_and_country_anonymous(request)

        if 'currency' in data:
            currency = data['currency']
        coupon = None
        if 'coupon' in self.context and self.context['coupon']:
            coupon = self.context['coupon']
        expiration_date = timezone.now() + datetime.timedelta(days=14)

        if is_seller:
            stripe = self.context['stripe']
            user = User.objects.create_user(**data,
                                            is_verified=False,
                                            is_client=True,

                                            )

            plan = helpers.get_plan(currency)

            new_customer = stripe.Customer.create(
                description="freeCustomer_"+user.first_name+'_'+user.last_name,
                name=user.first_name+' '+user.last_name,
                email=user.email,
            )
            if coupon:

                subscription = stripe.Subscription.create(
                    customer=new_customer['id'],
                    items=[
                        {"price": plan.stripe_price_id}
                    ],
                    trial_period_days="14",
                    coupon=coupon
                )
            else:
                subscription = stripe.Subscription.create(
                    customer=new_customer['id'],
                    items=[
                        {"price": plan.stripe_price_id}
                    ],
                    trial_period_days="14"
                )
            if coupon:
                PlanSubscription.objects.create(
                    user=user,
                    subscription_id=subscription["id"],
                    plan_unit_amount=plan.unit_amount,
                    plan_currency=plan.currency,
                    status=subscription['status'],
                    plan_price_label=plan.price_label,
                    plan_type=plan.type,
                    product_id=plan.stripe_product_id,
                    coupon=coupon
                )
            else:
                PlanSubscription.objects.create(
                    user=user,
                    subscription_id=subscription["id"],
                    plan_unit_amount=plan.unit_amount,
                    plan_currency=plan.currency,
                    status=subscription['status'],
                    plan_price_label=plan.price_label,
                    plan_type=plan.type,
                    product_id=plan.stripe_product_id,
                )
            user.country = country
            user.seller_view = True
            user.is_seller = True
            user.is_free_trial = True
            user.free_trial_expiration = expiration_date
            user.stripe_plan_customer_id = new_customer["id"]
            user.currency = currency
            user.save()

        else:
            user = User.objects.create_user(**data,
                                            is_verified=False,
                                            is_client=True,
                                            currency=currency,
                                            country=country
                                            )
        token, created = Token.objects.get_or_create(
            user=user)

        current_login_ip = helpers.get_client_ip(request)

        if UserLoginActivity.objects.filter(user=user).exists():
            user_login_activity = UserLoginActivity.objects.filter(
                user=user)[0]
            if user_login_activity.login_IP != current_login_ip:
                if Token.objects.filter(user=user).exists():
                    last_token = Token.objects.get(user=user)
                    last_token.delete()
            UserLoginActivity.objects.filter(
                login_username=user.username).delete()

        user_agent_info = request.META.get(
            'HTTP_USER_AGENT', '<unknown>')[:255],
        user_login_activity_log = UserLoginActivity(login_IP=helpers.get_client_ip(request),
                                                    user=user,
                                                    login_username=user.username,
                                                    user_agent_info=user_agent_info,
                                                    status=UserLoginActivity.SUCCESS)
        user_login_activity_log.save()

        send_confirmation_email(user)

        if 'payload' in self.context:
            # Add to contacts user to from user
            payload = self.context['payload']

            from_user = get_object_or_404(User, id=payload['from_user'])
            from_user.contacts.add(user)
            from_user.save()
            user.contacts.add(from_user)
            user.save()

        return user, token.key


class UserLoginSerializer(serializers.Serializer):
    """User login serializer.

    Handle the login request
    """

    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        """Check credentials."""
        # Validation with email or password

        email = data['email']
        password = data['password']
        request = self.context['request']
        regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
        # for custom mails use: '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w+$'
        if email and password:
            if re.search(regex, email):
                user_request = get_object_or_404(
                    User,
                    email=email
                )
                email = user_request.username
            # Check if user set email

        users = User.objects.filter(username=email, account_deactivated=True)

        if users.exists():
            raise serializers.ValidationError(
                'This account has already been desactivated')

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError(
                'Invalid credentials')

        if user:
            current_login_ip = helpers.get_client_ip(request)

            if UserLoginActivity.objects.filter(user=user).exists():
                user_login_activity = UserLoginActivity.objects.filter(
                    user=user)[0]
                if user_login_activity.login_IP != current_login_ip:
                    if Token.objects.filter(user=user).exists():
                        last_token = Token.objects.get(user=user)
                        last_token.delete()
                UserLoginActivity.objects.filter(
                    user=user).delete()
            user_agent_info = request.META.get(
                'HTTP_USER_AGENT', '<unknown>')[:255],
            user_login_activity_log = UserLoginActivity(login_IP=helpers.get_client_ip(request),
                                                        user=user,
                                                        login_username=user.username,
                                                        user_agent_info=user_agent_info,
                                                        status=UserLoginActivity.SUCCESS)
            user_login_activity_log.save()

        self.context['user'] = user
        return data

    def create(self, data):
        """Generate or retrieve new token."""

        token, created = Token.objects.get_or_create(user=self.context['user'])
        return self.context['user'], token.key


class AccountVerificationSerializer(serializers.Serializer):
    """Acount verification serializer."""

    token = serializers.CharField()

    def validate_token(self, data):
        """Verifiy token is valid."""
        try:
            payload = jwt.decode(data, settings.SECRET_KEY,
                                 algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise serializers.ValidationError('Verification link has expired')
        except jwt.PyJWTError:
            raise serializers.ValidationError('Invalid token')
        if payload['type'] != 'email_confirmation':
            raise serializers.ValidationError('Invalid token')
        self.context['payload'] = payload
        return data

    def save(self):
        """Update user's verified status."""
        payload = self.context['payload']
        user = User.objects.get(username=payload['user'])
        if user.is_verified:
            raise serializers.ValidationError('Your account is already validated')

        user.is_verified = True
        user.save()


class IsEmailAvailableSerializer(serializers.Serializer):
    """Acount verification serializer."""

    email = serializers.CharField()

    def validate(self, data):
        """Update user's verified status."""

        email = data['email']

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('This email is already in use')

        return {"email": email}


class IsCouponAvailableSerializer(serializers.Serializer):
    """Acount verification serializer."""

    coupon = serializers.CharField()

    def validate(self, data):
        """Update user's verified status."""

        coupon = data['coupon']
        stripe = self.context['stripe']
        try:
            stripe_coupon = stripe.Coupon.retrieve(coupon)
            if not stripe_coupon['valid']:
                raise serializers.ValidationError('This coupon is not valid')

        except:
            raise serializers.ValidationError('This coupon does not exist')

        return {"coupon": coupon}


class IsUsernameAvailableSerializer(serializers.Serializer):
    """Acount verification serializer."""

    username = serializers.CharField()

    def validate(self, data):
        """Update user's verified status."""

        username = data['username']

        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError('This username is already in use')

        return True


class ChangeEmailSerializer(serializers.Serializer):
    """Acount verification serializer."""

    email = serializers.CharField()

    def validate(self, data):
        """Update user's verified status."""

        email = data['email']
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('This email is already in use')

        user = self.context['user']

        send_change_email_email(user, email)
        return {'email': email, 'user': user}


class ValidateChangeEmail(serializers.Serializer):
    """Acount verification serializer."""

    token = serializers.CharField()

    def validate_token(self, data):
        """Verifiy token is valid."""
        try:
            payload = jwt.decode(data, settings.SECRET_KEY,
                                 algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise serializers.ValidationError('Verification link has expired')
        except jwt.PyJWTError:
            raise serializers.ValidationError('Invalid token')
        if payload['type'] != 'change_email':
            raise serializers.ValidationError('Invalid token')
        self.context['payload'] = payload
        return data

    def save(self):
        """Update user's verified status."""
        payload = self.context['payload']
        user = User.objects.get(username=payload['user'])
        email = payload['email']

        user.email = email
        user.save()
        return email


class ForgetPasswordSerializer(serializers.Serializer):
    """Acount verification serializer."""

    email = serializers.CharField()

    def validate(self, data):
        """Update user's verified status."""

        email = data['email']

        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError('This email does not exists')

        send_reset_password_email(email)
        return {'email': email}


class ResetPasswordSerializer(serializers.Serializer):
    """Acount verification serializer."""

    token = serializers.CharField()
    password = serializers.CharField(min_length=8, max_length=64)
    confirm_password = serializers.CharField(min_length=8, max_length=64)

    def validate_token(self, data):
        """Verifiy token is valid."""
        try:
            payload = jwt.decode(data, settings.SECRET_KEY,
                                 algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise serializers.ValidationError('Verification link has expired')
        except jwt.PyJWTError:
            raise serializers.ValidationError('Invalid token')
        if payload['type'] != 'email_confirmation':
            raise serializers.ValidationError('Invalid token')
        self.context['payload'] = payload
        return data

    def validate(self, data):

        password = data['password']
        confirm_password = data['confirm_password']
        if password != confirm_password:
            raise serializers.ValidationError('Passwords don\'t match')
        return data

    def save(self):
        """Update user's verified status."""
        username = self.context['payload']['user']

        password = self.data['password']
        user = User.objects.get(username=username)
        user.set_password(password)
        user.save()
        return user


class AddInstructorAccountsSerializer(serializers.Serializer):
    def validate(self, data):
        user = self.instance
        accounts_acquired = self.context['accounts_acquired']
        data = {
            'accounts_acquired': accounts_acquired,
        }
        return data

    def update(self, instance, validated_data):

        accounts_acquired = validated_data['accounts_acquired']

        instance.teacher.current_accounts = accounts_acquired['accounts']

        instance.teacher.accounts_to_create_left = int(
            accounts_acquired['accounts']) - instance.teacher.instructors.count()

        instance.teacher.currency = accounts_acquired['currency']
        instance.teacher.accounts_price = accounts_acquired['price']

        instance.teacher.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """User login serializer.

    Handle the login request
    """
    password = serializers.CharField(min_length=8, max_length=64)
    new_password = serializers.CharField(min_length=8, max_length=64)
    repeat_password = serializers.CharField(min_length=8, max_length=64)

    def validate(self, data):
        """Check credentials."""
        # Validation with email or password
        regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
        # for custom mails use: '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w+$'
        user = self.context['request'].user
        password = data['password']
        email = user.email
        if email and password:
            if re.search(regex, email):
                user_request = get_object_or_404(
                    User,
                    email=email
                )
                email = user_request.username
            # Check if user set email

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError('Current password is not correct')
        new_password = data['new_password']
        repeat_password = data['repeat_password']
        if new_password != repeat_password:
            raise serializers.ValidationError('Passwords not match')
        user.set_password(new_password)
        user.password_changed = True
        user.save()

        return data


class InviteUserSerializer(serializers.Serializer):
    """Acount verification serializer."""

    email = serializers.CharField()
    type = serializers.CharField()
    message = serializers.CharField(allow_blank=True)

    def validate(self, data):
        """Update user's verified status."""

        email = data['email']
        type = data['type']
        message = data['message']
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('This user already exists')
        if(type != "seller" and type != "buyer"):
            raise serializers.ValidationError('Type not valid')

        request = self.context['request']
        user = request.user

        send_invitation_email(user, email, message, type)
        return data


class InviteUserSerializer(serializers.Serializer):
    """Acount verification serializer."""

    email = serializers.CharField()
    type = serializers.CharField()
    message = serializers.CharField(allow_blank=True)

    def validate(self, data):
        """Update user's verified status."""

        email = data['email']
        type = data['type']
        message = data['message']
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('This user already exists')
        if(type != "seller" and type != "buyer"):
            raise serializers.ValidationError('Type not valid')

        request = self.context['request']
        user = request.user

        send_invitation_email(user, email, message, type)
        return data


class StripeConnectSerializer(serializers.Serializer):
    """Acount verification serializer."""

    auth_code = serializers.CharField()

    def validate(self, data):
        """Update user's verified status."""
        stripe = self.context['stripe']
        user = self.context['request'].user
        auth_code = data["auth_code"]
        if user.stripe_account_id != None and user.stripe_account_id != '':
            raise serializers.ValidationError('This user already is connected to stripe')
        response = stripe.OAuth.token(
            grant_type='authorization_code',
            code=auth_code,
        )

        connected_account_id = response['stripe_user_id']

        self.context['connected_account_id'] = connected_account_id

        if User.objects.filter(stripe_account_id=connected_account_id).exists():
            raise serializers.ValidationError('This account is already in use')

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

        return data

    def update(self, instance, validated_data):
        stripe = self.context['stripe']
        user = instance
        connected_account_id = self.context['connected_account_id']
        stripe_dashboard_url = stripe.Account.create_login_link(
            connected_account_id
        )
        user.stripe_account_id = connected_account_id
        user.stripe_dashboard_url = stripe_dashboard_url["url"]
        user.save()
        return {"stripe_account_id": user.stripe_account_id, "stripe_dashboard_url": user.stripe_dashboard_url}


class PaypalConnectSerializer(serializers.Serializer):
    """Paypal connect serializer serializer."""

    email = serializers.CharField()
    email_confirmation = serializers.CharField()

    def validate(self, data):
        """Update user's verified status."""
        email = data['email']
        email_confirmation = data['email_confirmation']
        if email != email_confirmation:
            raise serializers.ValidationError('Emails don\'t match')

        return data

    def update(self, instance, validated_data):
        user = instance
        email = validated_data['email']
        user.paypal_email = email
        user.save()

        return {"email": email}


class StripeSellerSubscriptionSerializer(serializers.Serializer):
    """Acount verification serializer."""

    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    payment_method_id = serializers.CharField(required=True)
    card_name = serializers.CharField(required=True)
    city = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    line1 = serializers.CharField(required=False, allow_blank=True)
    line2 = serializers.CharField(required=False, allow_blank=True)
    postal_code = serializers.CharField(required=True)
    state = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Update user's verified status."""
        stripe = self.context['stripe']
        request = self.context['request']
        user = request.user
        payment_method_id = None

        if "payment_method_id" in data and data["payment_method_id"]:
            payment_method_id = data["payment_method_id"]
        else:
            raise serializers.ValidationError(
                'There is no payment method')

        currency, country = helpers.get_currency_and_country(request)
        subscriptions_queryset = PlanSubscription.objects.filter(user=user, cancelled=False)

        if subscriptions_queryset.exists():

            plan_subscription = subscriptions_queryset.first()
            plan_currency = plan_subscription.plan_currency

            if currency != plan_currency:
                plan = helpers.get_plan(currency)

                subscription = stripe.Subscription.retrieve(plan_subscription.subscription_id)

                stripe.Subscription.modify(
                    subscription["id"],
                    cancel_at_period_end=False,
                    proration_behavior=None,
                    items=[
                        {
                            'id': subscription['items']['data'][0].id,
                            "price": plan.stripe_price_id,
                        },
                    ]
                )
                plan_subscription.plan_type = plan.type
                plan_subscription.plan_currency = plan.currency
                plan_subscription.plan_unit_amount = plan.unit_amount
                plan_subscription.plan_price_label = plan.price_label
                plan_subscription.save()
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.stripe_plan_customer_id,
            )
            stripe.Customer.modify(
                user.stripe_plan_customer_id,
                address={
                    "city": data.get('city', " "),
                    "country": data.get('country', " "),
                    "line1": data.get('line1', " "),
                    "line2": data.get('line2', " "),
                    "postal_code": data.get('postal_code', " "),
                    "state": data.get('state', " "),
                },
                email=data.get('email', " "),
                name=data.get('first_name', " ")+"_"+data.get('last_name', " "),
                invoice_settings={
                    "default_payment_method": payment_method_id
                }
            )
            stripe.PaymentMethod.modify(
                payment_method_id,
                billing_details={
                    "name": data.get('card_name', " "),
                }
            )

        else:
            plan = helpers.get_plan(user.currency)

            subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[
                    {"price": plan.stripe_price_id}
                ],
            )
            plan_subscription = PlanSubscription.objects.create(
                user=user,
                subscription_id=subscription["id"],
                plan_unit_amount=plan.unit_amount,
                plan_currency=plan.currency,
                plan_price_label=plan.price_label,
                plan_type=plan.type,
                product_id=plan.stripe_product_id
            )
            user.seller_view = True
            user.is_seller = True
            user.have_active_plan = True
            user.save()

        # Create customer if not exists
        user.have_active_plan = True
        return data

    def update(self, instance, validated_data):

        instance.plan_default_payment_method = validated_data['payment_method_id']
        instance.save()
        return instance


class SellerChangePaymentMethodSerializer(serializers.Serializer):
    """Acount verification serializer."""

    payment_method_id = serializers.CharField(required=True)

    def validate(self, data):
        """Update user's verified status."""
        request = self.context['request']
        user = request.user
        subscriptions_queryset = PlanSubscription.objects.filter(user=user, cancelled=False)

        if not subscriptions_queryset.exists():
            raise serializers.ValidationError(
                "User have not a plan subscription")

        return data

    def update(self, instance, validated_data):

        instance.plan_default_payment_method = validated_data['payment_method_id']
        instance.save()
        return instance


class SellerCancelSubscriptionSerializer(serializers.Serializer):
    """Acount verification serializer."""

    def validate(self, data):
        """Update user's verified status."""
        stripe = self.context['stripe']
        user = self.context['request'].user
        subscriptions_queryset = PlanSubscription.objects.filter(user=user, cancelled=False)

        if not subscriptions_queryset.exists():
            raise serializers.ValidationError(
                "User have not a plan subscription")

        plan_subscription = subscriptions_queryset.first()
        stripe.Subscription.modify(
            plan_subscription.subscription_id,
            cancel_at_period_end=True
        )
        self.context['plan_subscription'] = plan_subscription

        return data

    def update(self, instance, validated_data):
        plan_subscription = self.context['plan_subscription']
        plan_subscription.to_be_cancelled = True
        plan_subscription.save()
        return instance


class SellerReactivateSubscriptionSerializer(serializers.Serializer):
    """Acount verification serializer."""

    def validate(self, data):
        """Update user's verified status."""
        stripe = self.context['stripe']
        user = self.context['request'].user
        subscriptions_queryset = PlanSubscription.objects.filter(user=user, cancelled=False)

        if subscriptions_queryset.exists():

            plan_subscription = subscriptions_queryset.first()
            stripe.Subscription.modify(
                plan_subscription.subscription_id,
                cancel_at_period_end=False
            )
        else:
            plan = helpers.get_plan(user.currency)

            subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[
                    {"price": plan.stripe_price_id}
                ],
            )
            plan_subscription = PlanSubscription.objects.create(
                user=user,
                subscription_id=subscription["id"],
                plan_unit_amount=plan.unit_amount,
                plan_currency=plan.currency,
                plan_price_label=plan.price_label,
                plan_type=plan.type,
                product_id=plan.stripe_product_id
            )
            user.seller_view = True
            user.is_seller = True
            user.have_active_plan = True
            user.save()
        self.context['plan_subscription'] = plan_subscription

        return data

    def update(self, instance, validated_data):
        plan_subscription = self.context['plan_subscription']
        plan_subscription.to_be_cancelled = False
        plan_subscription.save()
        return instance


class BecomeASellerSerializer(serializers.Serializer):
    """Acount verification serializer."""

    def validate(self, data):
        """Update user's verified status."""
        stripe = self.context['stripe']
        request = self.context['request']
        user = request.user

        if user.is_seller:
            raise serializers.ValidationError(
                'User already is a seller')

        currency, country = helpers.get_currency_and_country(request)

        plan = helpers.get_plan(currency)

        new_customer = stripe.Customer.create(
            description="freeCustomer_"+user.first_name+'_'+user.last_name,
            name=user.first_name+' '+user.last_name,
            email=user.email,
        )

        subscription = stripe.Subscription.create(
            customer=new_customer['id'],
            items=[
                {"price": plan.stripe_price_id}
            ],
            trial_period_days="14",
        )
        PlanSubscription.objects.create(
            user=user,
            subscription_id=subscription["id"],
            plan_unit_amount=plan.unit_amount,
            plan_currency=plan.currency,
            plan_price_label=plan.price_label,
            plan_type=plan.type,
            status=subscription['status'],
            product_id=plan.stripe_product_id
        )
        self.context['new_customer_id'] = new_customer['id']

        return data

    def update(self, instance, validated_data):
        expiration_date = timezone.now() + datetime.timedelta(days=14)
        new_customer_id = self.context['new_customer_id']
        instance.is_seller = True
        instance.is_free_trial = True
        instance.free_trial_expiration = expiration_date
        instance.have_active_plan = True
        instance.stripe_plan_customer_id = new_customer_id

        instance.save()
        return instance


class AttachPlanPaymentMethodSerializer(serializers.Serializer):
    """Acount verification serializer."""
    payment_method_id = serializers.CharField(required=True)
    card_name = serializers.CharField(required=True)

    def validate(self, data):
        """Update user's verified status."""
        stripe = self.context['stripe']
        user = self.context['request'].user
        payment_method_id = data['payment_method_id']
        payment_method_object = stripe.PaymentMethod.retrieve(
            payment_method_id,
        )
        payment_methods = helpers.get_payment_methods(stripe, user.stripe_plan_customer_id)
        if payment_methods:
            for payment_method in payment_methods:
                if payment_method.card.fingerprint == payment_method_object.card.fingerprint:
                    raise serializers.ValidationError(
                        'This payment method is already added')

        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=user.stripe_plan_customer_id,
        )
        stripe.PaymentMethod.modify(
            payment_method_id,
            billing_details={
                "name": data.get('card_name', " "),
            }
        )

        return data

    def update(self, instance, validated_data):

        return instance


class AttachPaymentMethodSerializer(serializers.Serializer):
    """Acount verification serializer."""
    payment_method_id = serializers.CharField(required=True)
    card_name = serializers.CharField(required=True)

    def validate(self, data):
        """Update user's verified status."""
        stripe = self.context['stripe']
        user = self.context['request'].user
        payment_method_id = data['payment_method_id']
        payment_method_object = stripe.PaymentMethod.retrieve(
            payment_method_id,
        )
        if not user.stripe_customer_id:
            new_customer = stripe.Customer.create(
                description="freeCustomer_"+user.first_name+'_'+user.last_name,
                name=user.first_name+' '+user.last_name,
                email=user.email,
            )
            user.stripe_customer_id = new_customer['id']
            user.save()

        payment_methods = helpers.get_payment_methods(stripe, user.stripe_customer_id)
        if payment_methods:
            for payment_method in payment_methods:
                if payment_method.card.fingerprint == payment_method_object.card.fingerprint:
                    raise serializers.ValidationError(
                        'This payment method is already added')

        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=user.stripe_customer_id,
        )
        if not payment_methods or len(payment_method) == 0:
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id
                }
            )
            user.default_payment_method = payment_method_id

        stripe.PaymentMethod.modify(
            payment_method_id,
            billing_details={
                "name": data.get('card_name', " "),
            }
        )

        return data

    def update(self, instance, validated_data):

        return instance


class DetachPaymentMethodSerializer(serializers.Serializer):
    """Acount verification serializer."""
    payment_method_id = serializers.CharField()

    def validate(self, data):
        """Update user's verified status."""
        stripe = self.context['stripe']
        user = self.context['request'].user
        payment_method_id = data['payment_method_id']
        if payment_method_id == user.plan_default_payment_method:
            raise serializers.ValidationError(
                'This payment method is attached to a plan subscription')

        stripe.PaymentMethod.detach(
            "pm_1ICOvTCob7soW4zYIiXsCA4C",
        )

        return data

    def update(self, instance, validated_data):

        return instance
