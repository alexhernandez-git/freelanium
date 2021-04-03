"""Celery tasks."""

# Django
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.module_loading import import_string

# Models
from api.users.models import User, Earning
from rest_framework.authtoken.models import Token
from api.notifications.models import NotificationUser, notifications
from api.activities.models import Activity, OfferActivity, DeliveryActivity, CancelOrderActivity
from api.orders.models import Order
from djmoney.money import Money

# Celery
from celery.decorators import task

# Utilities
import jwt
import time
from django.utils import timezone
from api.utils import helpers
import re


@task(name='send_feedback_email', max_retries=3)
def send_feedback_email(user, message):
    """Check if the free trial has ended and turn off"""

    subject = 'Feedback from @{}'.format(
        user.email)

    from_email = 'Freelanium <no-reply@freelanium.com>'
    content = render_to_string(
        'emails/users/feedback_email.html',
        {'user': user, 'message': message}
    )
    msg = EmailMultiAlternatives(subject, content, from_email, ["support@freelanium.com", "freelanium@gmail.com"], [])
    msg.attach_alternative(content, "text/html")
    msg.send()


@task(name='send_confirmation_email', max_retries=3)
def send_confirmation_email(user):
    """Send account verification link to given user."""

    verification_token = helpers.gen_verification_token(user)
    subject = 'Welcome @{}! Verify your account to start using Freelanium'.format(
        user.username)
    from_email = 'Freelanium <no-reply@freelanium.com>'
    content = render_to_string(
        'emails/users/account_verification.html',
        {'token': verification_token, 'user': user}
    )
    msg = EmailMultiAlternatives(subject, content, from_email, [user.email])
    msg.attach_alternative(content, "text/html")
    msg.send()


@task(name='send_change_email_email', max_retries=3)
def send_change_email_email(user, new_email):
    """Send account verification link to given user."""

    verification_token = helpers.gen_new_email_token(user, new_email)
    subject = 'Welcome @{}! Change your email'.format(
        user.username)
    from_email = 'Freelanium <no-reply@freelanium.com>'
    content = render_to_string(
        'emails/users/change_email.html',
        {'token': verification_token, 'user': user}
    )
    msg = EmailMultiAlternatives(subject, content, from_email, [user.email])
    msg.attach_alternative(content, "text/html")
    msg.send()


@task(name='send_reset_password', max_retries=3)
def send_reset_password_email(user_email):
    """Send account verification link to given user."""
    user = User.objects.get(email=user_email)
    verification_token = helpers.gen_verification_token(user)

    subject = 'Reset your password'
    from_email = 'Freelanium <no-reply@freelanium.com>'
    content = render_to_string(
        'emails/users/reset_password.html',
        {'token': verification_token, 'user': user}
    )
    msg = EmailMultiAlternatives(subject, content, from_email, [user.email])
    msg.attach_alternative(content, "text/html")
    msg.send()


@task(name='send_invitation_email', max_retries=3)
def send_invitation_email(user, email, message, type):
    """Send account verification link to given user."""

    verification_token = helpers.get_invitation_token(user, email)
    subject = 'Welcome! @{} has invited you '.format(
        user.username)
    from_email = 'Freelanium <no-reply@freelanium.com>'
    content = render_to_string(
        'emails/users/user_invitation.html',
        {'token': verification_token, 'user': user, 'message': message, 'type': type}
    )
    msg = EmailMultiAlternatives(subject, content, from_email, [email])
    msg.attach_alternative(content, "text/html")
    msg.send()


@task(name='send_offer', max_retries=3)
def send_offer(user, email, user_exists, offer_id, buyer_id=None):
    """Send account verification link to given user."""
    user_token = None
    verification_token = None

    if user_exists:
        verification_token = helpers.get_user_token(buyer_id)

    subject = '@{} sent you an offer '.format(
        user.username)
    from_email = 'Freelanium <no-reply@freelanium.com>'

    content = render_to_string(
        'emails/users/order_offer.html',
        {'token': verification_token, 'user': user, 'user_exists': user_exists, 'offer': offer_id}
    )
    msg = EmailMultiAlternatives(subject, content, from_email, [email])
    msg.attach_alternative(content, "text/html")
    msg.send()


# @task(name='check_if_free_trial_have_ended')
# def check_if_free_trial_have_ended():
#     """Check if the free trial has ended and turn off"""
#     now = timezone.now()

#     # Update rides that have already finished
#     users = User.objects.filter(
#         free_trial_expiration__gte=now,
#         is_free_trial=True
#     )
#     users.update(is_free_trial=False, passed_free_trial_once=True)
#     print("Users that has been updated")
#     print("Total: "+str(users.count()))
#     for user in users:
#         print("---------------------------------")
#         print(user.username)


@task(name='send_have_messages_from_email', max_retries=3)
def send_have_messages_from_email(sent_to, sent_by):
    """Check if the free trial has ended and turn off"""

    subject = 'New messages from @{}'.format(
        sent_by.username)

    from_email = 'Freelanium <no-reply@freelanium.com>'
    content = render_to_string(
        'emails/users/new_messages.html',
        {'user': sent_by}
    )
    msg = EmailMultiAlternatives(subject, content, from_email, [sent_to.email])
    msg.attach_alternative(content, "text/html")
    msg.send()


@task(name='send_activity_notification', max_retries=3)
def send_activity_notification(activity, type):
    """send_activity_notification."""
    print(type)

    def offer_accepted_email():
        order = Order.objects.get(offer=activity.offer)
        return render_to_string(
            'emails/users/order_offer.html',
            {'user': order.buyer, 'order': order.id}
        ), order.seller, '@{} has accepted the offer '.format(
            order.buyer.username)

    def order_delivery_email():

        order = activity.delivery.order
        return render_to_string(
            'emails/users/order_delivery.html',
            {'user': order.seller, 'order': order.id}
        ), order.buyer.email, '@{} has delivered the offer '.format(
            order.seller.username)

    def order_delivery_accepted_email():
        order = activity.delivery.order
        return render_to_string(
            'emails/users/delivery_accepted.html',
            {'user': order.buyer, 'order': order.id}
        ), order.seller.email, '@{} has accepted the delivery '.format(
            order.buyer.username)

    def order_delivery_revision_email():
        order = activity.revision.order
        return render_to_string(
            'emails/users/delivery_revision.html',
            {'user': order.buyer, 'order': order.id}
        ), order.seller.email, '@{} has requested a delivery revision '.format(
            order.buyer.username)

    def order_cancelation_email():
        cancel_order = activity.cancel_order
        order = cancel_order.order
        issued_by = cancel_order.issued_by

        sent_to = None
        if issued_by == order.buyer:
            sent_to = order.seller
        else:
            sent_to = order.buyer

        return render_to_string(
            'emails/users/cancelation_request.html',
            {'user': issued_by, 'order': order.id}
        ), sent_to.email, '@{} has requested a cancelation '.format(
            issued_by.username)

    def cancelation_accepted_email():
        cancel_order = activity.cancel_order
        order = cancel_order.order
        issued_by = cancel_order.issued_by

        sent_by = None
        if issued_by == order.buyer:
            sent_by = order.seller
        else:
            sent_by = order.buyer

        return render_to_string(
            'emails/users/cancelation_request.html',
            {'user': issued_by, 'order': order.id}
        ), issued_by.email, '@{} has accepted the cancelation '.format(
            sent_by.username)

    def cancelation_not_accepted_email():
        cancel_order = activity.cancel_order
        order = cancel_order.order
        issued_by = cancel_order.issued_by

        sent_by = None
        if issued_by == order.buyer:
            sent_by = order.seller
        else:
            sent_by = order.buyer

        return render_to_string(
            'emails/users/cancelation_request.html',
            {'user': issued_by, 'order': order.id}
        ), sent_by.email, '@{} has not accepted the cancelation '.format(
            issued_by.username)

    from_email = 'Freelanium <no-reply@freelanium.com>'

    switcher = {
        Activity.OFFER+OfferActivity.ACCEPTED: offer_accepted_email,
        Activity.DELIVERY+DeliveryActivity.PENDENDT: order_delivery_email,
        Activity.DELIVERY+DeliveryActivity.ACCEPTED: order_delivery_accepted_email,
        Activity.REVISION: order_delivery_revision_email,
        Activity.CANCEL+CancelOrderActivity.PENDENDT: order_cancelation_email,
        Activity.CANCEL+CancelOrderActivity.ACCEPTED: cancelation_accepted_email,
        Activity.CANCEL+CancelOrderActivity.CANCELLED: cancelation_not_accepted_email,
    }

    get_email_data_function = switcher.get(type, None)

    content, email, subject = get_email_data_function()

    if content and email and subject:

        msg = EmailMultiAlternatives(subject, content, from_email, [email])
        msg.attach_alternative(content, "text/html")
        msg.send()


@task(name='check_if_pending_clearance_has_ended', max_retries=3)
def check_if_pending_clearance_has_ended():
    """Check if pending clearance has ended."""
    today = timezone.now()

    earnings = Earning.objects.filter(
        type__in=[Earning.ORDER_REVENUE, Earning.REFUND],
        available_for_withdrawn_date__lt=today, setted_to_available_for_withdrawn=False)

    for earning in earnings:
        print(earning.amount)
        user = earning.user
        if user:
            pending_clearance_substracted = user.pending_clearance - earning.amount
            available_for_withdrawn_add = earning.amount
            if pending_clearance_substracted < Money(amount=0, currency="USD"):
                available_for_withdrawn_add = earning.amount + pending_clearance_substracted
                pending_clearance_substracted = 0

            user.pending_clearance = pending_clearance_substracted

            user.available_for_withdrawal += available_for_withdrawn_add

            user.save()

            earning.setted_to_available_for_withdrawn = True
            earning.save()
            return available_for_withdrawn_add.amount
