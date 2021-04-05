"""Users serializers."""

# Django REST Framework
from rest_framework import serializers

# Django
from django.conf import settings
from django.shortcuts import get_object_or_404


# Models
from api.orders.models import CancelOrder, Order
from api.activities.models import Activity, CancelOrderActivity
from api.users.models import User, Earning
from api.chats.models import Message, Chat, SeenBy
from djmoney.models.fields import Money


# Serializers
from api.orders.serializers import OrderModelSerializer
from api.users.serializers import UserModelSerializer

# Utils
from datetime import timedelta
from django.utils import timezone


class CancelOrderModelSerializer(serializers.ModelSerializer):
    """CancelOrder model serializer."""
    order = OrderModelSerializer(read_only=True)
    issued_by = UserModelSerializer(read_only=True)

    class Meta:
        """Meta class."""

        model = CancelOrder
        fields = (
            "id",
            "order",
            "issued_by",
            "reason",
            "status",
        )
        extra_kwargs = {"status": {"required": False, "allow_null": True}}

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        validated_data['issued_by'] = user
        order = self.context['order']
        validated_data['order'] = order
        cancel_order = CancelOrder.objects.create(**validated_data)
        activity = Activity.objects.create(
            type=Activity.CANCEL,
            order=order
        )
        CancelOrderActivity.objects.create(
            activity=activity,
            cancel_order=cancel_order
        )

        seller = order.seller
        buyer = order.buyer

        issued_by = user
        issued_to = None
        if issued_by == seller:
            issued_to = buyer
        else:
            issued_to = seller

        chats = Chat.objects.filter(participants=issued_by)
        chats = chats.filter(participants=issued_to)

        chat_instance = None
        if chats.exists():
            for chat in chats:
                if chat.participants.all().count() == 2:
                    chat_instance = chat

        if not chat_instance:

            chat_instance = Chat.objects.create()

            chat_instance.participants.add(issued_to)
            chat_instance.participants.add(issued_by)
            chat_instance.save()

        # Create the message

        message = Message.objects.create(chat=chat_instance, activity=activity, sent_by=issued_by)
        chat_instance.last_message = message
        chat_instance.save()
        # Set message seen
        seen_by, created = SeenBy.objects.get_or_create(chat=chat_instance, user=issued_by)
        if seen_by.message != chat_instance.last_message:

            seen_by.message = chat_instance.last_message
            seen_by.save()
        return cancel_order


class CancelOrderCancelationModelSerializer(serializers.ModelSerializer):
    """CancelOrder model serializer."""
    order = OrderModelSerializer(read_only=True)
    issued_by = UserModelSerializer(read_only=True)

    class Meta:
        """Meta class."""

        model = CancelOrder
        fields = (
            "id",
            "order",
            "issued_by",
            "reason",
            "status",
        )
        read_only_fields = (
            "id",
            "order",
            "issued_by",
            "reason",
            "status",
        )

    def validate(self, data):
        cancel_order = self.instance
        request = self.context['request']
        user = request.user
        if user == cancel_order.issued_by:
            raise serializers.ValidationError('You are not allowed to do this action')
        if cancel_order.status == CancelOrder.ACCEPTED:
            raise serializers.ValidationError('This order is already accepted')
        elif cancel_order.status == CancelOrder.CANCELLED:
            raise serializers.ValidationError('This order is already cancelled')
        return data

    def update(self, instance,  validated_data):
        order = instance.order
        activity = Activity.objects.create(
            type=Activity.CANCEL,
            order=order
        )
        CancelOrderActivity.objects.create(
            activity=activity,
            cancel_order=instance,
            status=CancelOrderActivity.CANCELLED
        )

        seller = order.seller
        buyer = order.buyer

        issued_by = instance.issued_by
        issued_to = None
        if issued_by == seller:
            issued_to = buyer
        else:
            issued_to = seller

        chats = Chat.objects.filter(participants=issued_by)
        chats = chats.filter(participants=issued_to)

        chat_instance = None
        if chats.exists():
            for chat in chats:
                if chat.participants.all().count() == 2:
                    chat_instance = chat

        if not chat_instance:

            chat_instance = Chat.objects.create()

            chat_instance.participants.add(issued_to)
            chat_instance.participants.add(issued_by)
            chat_instance.save()

        # Create the message

        message = Message.objects.create(chat=chat_instance, activity=activity, sent_by=issued_by)
        chat_instance.last_message = message
        chat_instance.save()
        # Set message seen
        seen_by, created = SeenBy.objects.get_or_create(chat=chat_instance, user=issued_by)
        if seen_by.message != chat_instance.last_message:

            seen_by.message = chat_instance.last_message
            seen_by.save()

        instance.status = CancelOrder.CANCELLED
        instance.save()
        return instance


class AcceptOrderCancelationModelSerializer(serializers.ModelSerializer):
    """CancelOrder model serializer."""
    order = OrderModelSerializer(read_only=True)
    issued_by = UserModelSerializer(read_only=True)

    class Meta:
        """Meta class."""

        model = CancelOrder
        fields = (
            "id",
            "order",
            "issued_by",
            "reason",
            "status",
        )
        read_only_fields = (
            "id",
            "order",
            "issued_by",
            "reason",
            "status",
        )

    def validate(self, data):
        cancel_order = self.instance
        request = self.context['request']
        user = request.user

        if user == cancel_order.issued_by:
            raise serializers.ValidationError('You are not allowed to do this action')

        if cancel_order.order.type == Order.RECURRENT_ORDER:
            raise serializers.ValidationError('Recurrent orders can`t be cancelled')

        if cancel_order.status == CancelOrder.ACCEPTED:
            raise serializers.ValidationError('This order is already accepted')

        elif cancel_order.status == CancelOrder.CANCELLED:
            raise serializers.ValidationError('This order is already cancelled')
        return data

    def update(self, instance,  validated_data):

        order = instance.order

        order.status = Order.CANCELLED
        if order.type == Order.HOLDING_PAYMENT_ORDER:
            # Return de money to user as credits
            buyer = order.buyer
            buyer.net_income = buyer.net_income + order.due_to_seller
            Earning.objects.create(
                user=buyer,
                amount=order.due_to_seller,
                type=Earning.REFUND,
                available_for_withdrawn_date=timezone.now() + timedelta(days=14)
            )

            buyer.pending_clearance = buyer.pending_clearance + order.due_to_seller
            buyer.used_for_purchases = buyer.used_for_purchases - order.used_credits
            buyer.save()
        order.save()

        activity = Activity.objects.create(
            type=Activity.CANCEL,
            order=order
        )
        CancelOrderActivity.objects.create(
            activity=activity,
            cancel_order=instance,
            status=CancelOrderActivity.ACCEPTED
        )

        seller = order.seller
        buyer = order.buyer

        issued_by = instance.issued_by
        issued_to = None
        if issued_by == seller:
            issued_to = buyer
        else:
            issued_to = seller

        chats = Chat.objects.filter(participants=issued_by)
        chats = chats.filter(participants=issued_to)

        chat_instance = None
        if chats.exists():
            for chat in chats:
                if chat.participants.all().count() == 2:
                    chat_instance = chat

        if not chat_instance:

            chat_instance = Chat.objects.create()

            chat_instance.participants.add(issued_to)
            chat_instance.participants.add(issued_by)
            chat_instance.save()

        # Create the message

        message = Message.objects.create(chat=chat_instance, activity=activity, sent_by=issued_by)
        chat_instance.last_message = message
        chat_instance.save()
        # Set message seen
        seen_by, created = SeenBy.objects.get_or_create(chat=chat_instance, user=issued_by)
        if seen_by.message != chat_instance.last_message:

            seen_by.message = chat_instance.last_message
            seen_by.save()

        instance.status = CancelOrder.ACCEPTED
        instance.save()
        return instance


class UnsubscribeOrderModelSerializer(serializers.ModelSerializer):
    """CancelOrder model serializer."""
    order = OrderModelSerializer(read_only=True)
    issued_by = UserModelSerializer(read_only=True)

    class Meta:
        """Meta class."""

        model = CancelOrder
        fields = (
            "id",
            "order",
            "issued_by",
            "reason",
            "status",
        )
        extra_kwargs = {"status": {"required": False, "allow_null": True}}

    def validate(self, data):
        order = self.context['order']
        request = self.context['request']
        user = request.user
        if order.type != Order.RECURRENT_ORDER:
            raise serializers.ValidationError('This order type is not allowed')

        if user != order.buyer:
            raise serializers.ValidationError('You are not allowed to do this action')

        if order.status == Order.CANCELLED:
            raise serializers.ValidationError('This order is cancelled')

        return data

    def create(self, validated_data):
        stripe = self.context['stripe']
        request = self.context['request']
        user = request.user
        validated_data['issued_by'] = user
        order = self.context['order']
        validated_data['order'] = order

        stripe.Subscription.delete(order.subscription_id)
        order.status = Order.CANCELLED
        buyer = order.buyer

        if order.used_credits > Money(amount=0, currency="USD"):
            buyer.reserved_for_subscriptions -= order.used_credits
            buyer.pending_clearance -= order.pending_clearance
            Earning.objects.create(
                user=buyer,
                amount=order.used_credits,
                type=Earning.REFUND,
                available_for_withdrawn_date=timezone.now() + timedelta(days=14)
            )
            buyer.save()
        order.cancelled = True
        order.save()

        cancel_order = CancelOrder.objects.create(**validated_data)
        activity = Activity.objects.create(
            type=Activity.CANCEL,
            order=order
        )
        CancelOrderActivity.objects.create(
            activity=activity,
            cancel_order=cancel_order,
            status=CancelOrderActivity.ACCEPTED
        )

        seller = order.seller

        issued_by = user
        issued_to = None
        if issued_by == seller:
            issued_to = buyer
        else:
            issued_to = seller

        chats = Chat.objects.filter(participants=issued_by)
        chats = chats.filter(participants=issued_to)

        chat_instance = None
        if chats.exists():
            for chat in chats:
                if chat.participants.all().count() == 2:
                    chat_instance = chat

        if not chat_instance:

            chat_instance = Chat.objects.create()

            chat_instance.participants.add(issued_to)
            chat_instance.participants.add(issued_by)
            chat_instance.save()

        # Create the message

        message = Message.objects.create(chat=chat_instance, activity=activity, sent_by=issued_by)
        chat_instance.last_message = message
        chat_instance.save()
        # Set message seen
        seen_by, created = SeenBy.objects.get_or_create(chat=chat_instance, user=issued_by)
        if seen_by.message != chat_instance.last_message:

            seen_by.message = chat_instance.last_message
            seen_by.save()
        return cancel_order
