"""Users serializers."""

# Django REST Framework
from rest_framework import serializers

# Django
from django.conf import settings
from django.shortcuts import get_object_or_404


# Models
from api.orders.models import Order
from api.users.models import User, Earning
from api.activities.models import OfferActivity, Activity, CancelOrderActivity
from api.orders.models import Offer, OrderPayment
from api.chats.models import Message, Chat, SeenBy
from djmoney.models.fields import Money

# Serializers
from api.users.serializers import UserModelSerializer

# Utils
from api.utils import helpers
from datetime import timedelta
from django.utils import timezone


class OrderModelSerializer(serializers.ModelSerializer):
    """User model serializer."""
    seller = UserModelSerializer()
    buyer = UserModelSerializer()

    class Meta:
        """Meta class."""

        model = Order
        fields = (
            "__all__")

        read_only_fields = ("id",)


class AcceptOrderSerializer(serializers.Serializer):
    """Acount verification serializer."""
    payment_method_id = serializers.CharField()
    order = OrderModelSerializer(read_only=True)

    def validate(self, data):
        """Update user's verified status."""

        payment_method_id = data['payment_method_id']
        offer = self.context['offer']
        stripe = self.context['stripe']
        request = self.context['request']
        user = request.user

        offer_object = get_object_or_404(Offer, id=offer['id'])
        self.context['offer_object'] = offer_object
        # Check if offer is not accepted
        if offer_object.accepted:
            raise serializers.ValidationError(
                "This offer already has been accepted")

        # Check if the payload match with the offer
        if offer['type'] == Order.ONE_PAYMENT_ORDER == offer['type'] == Order.HOLDING_PAYMENT_ORDER or offer['type'] == Order.RECURRENT_ORDER:

            currencyRate, _ = helpers.get_currency_rate(user.currency, offer_object.rate_date)
            subtotal = float(offer_object.unit_amount.amount) * currencyRate

            available_for_withdrawal = (float(user.available_for_withdrawal.amount) +
                                        float(user.pending_clearance.amount)) * currencyRate
            used_credits = 0
            if available_for_withdrawal > 0:
                if available_for_withdrawal > subtotal:
                    used_credits = subtotal
                else:
                    diff = available_for_withdrawal - subtotal
                    used_credits = subtotal + diff
            fixed_price = 0.3 * currencyRate
            service_fee = ((subtotal - used_credits) * 5) / 100 + fixed_price
            unit_amount = subtotal + service_fee
            if round(
                    unit_amount, 2) != float(
                    offer['unit_amount']) or round(
                    used_credits, 2) != float(
                    offer['used_credits']):
                raise serializers.ValidationError(
                    "The data recieved not match with the offer")

        if offer['type'] == Order.TWO_PAYMENTS_ORDER:

            currencyRate, _ = helpers.get_currency_rate(user.currency, offer_object.rate_date)
            subtotal = float(offer_object.first_payment.amount) * currencyRate
            first_payment = subtotal
            payment_at_delivery = float(offer_object.payment_at_delivery.amount) * currencyRate

            available_for_withdrawal = (float(user.available_for_withdrawal.amount) +
                                        float(user.pending_clearance.amount)) * currencyRate
            used_credits = 0
            if available_for_withdrawal > 0:
                if available_for_withdrawal > subtotal:
                    used_credits = subtotal
                else:
                    diff = available_for_withdrawal - subtotal
                    used_credits = subtotal + diff
            fixed_price = 0.3 * currencyRate
            service_fee = ((subtotal - used_credits) * 5) / 100 + fixed_price
            unit_amount = subtotal + service_fee
            if round(unit_amount, 2) != float(offer['unit_amount']) \
                    or round(used_credits, 2) != float(offer['used_credits']) \
                    or round(first_payment, 2) != float(offer['first_payment']) \
                    or round(payment_at_delivery, 2) != float(offer['payment_at_delivery']):
                raise serializers.ValidationError(
                    "The data recieved not match with the offer")

        if not user.stripe_customer_id:

            new_customer = stripe.Customer.create(
                description="freeCustomer_"+user.first_name+'_'+user.last_name,
                name=user.first_name+' '+user.last_name,
                email=user.email,
            )
            user.stripe_customer_id = new_customer['id']
            user.save()
        stripe.Customer.modify(
            user.stripe_customer_id,
            invoice_settings={
                "default_payment_method": payment_method_id
            }
        )
        product = stripe.Product.create(name=offer['title'] + '_' + user.username)

        if not 'type' in offer:
            raise serializers.ValidationError(
                "Not a valid order type")
        if not 'seller' in offer:
            raise serializers.ValidationError(
                "Not seller in offer")
        if not 'unit_amount' in offer:
            raise serializers.ValidationError(
                "Not unit amount in offer")

        unit_amount = float(offer['unit_amount'])
        unit_amount_with_discount = unit_amount - float(offer['used_credits'])

        if not 'service_fee' in offer:
            raise serializers.ValidationError(
                "There is not service fee in this offer")

        price = None

        if offer['type'] == Order.ONE_PAYMENT_ORDER:

            price = stripe.Price.create(
                unit_amount=int(unit_amount_with_discount * 100),
                currency=user.currency,
                product=product['id']
            )
            stripe.InvoiceItem.create(
                customer=user.stripe_customer_id,
                price=price['id'],
            )
            invoice = stripe.Invoice.create(
                customer=user.stripe_customer_id,
                default_payment_method=payment_method_id

            )
            user.default_payment_method = payment_method_id
            user.save()
            invoice_paid = stripe.Invoice.pay(invoice['id'])
            self.context['price'] = price
            self.context['product'] = product

            self.context['invoice_paid'] = invoice_paid

        elif offer['type'] == Order.HOLDING_PAYMENT_ORDER:

            price = stripe.Price.create(
                unit_amount=int(unit_amount_with_discount * 100),
                currency=user.currency,
                product=product['id']
            )
            invoice_item = stripe.InvoiceItem.create(
                customer=user.stripe_customer_id,
                price=price['id'],
            )
            invoice = stripe.Invoice.create(
                customer=user.stripe_customer_id,
                default_payment_method=payment_method_id
            )
            user.default_payment_method = payment_method_id
            user.save()
            invoice_paid = stripe.Invoice.pay(invoice['id'])

            # Invoice paid succesfully, do actions

            self.context['price'] = price
            self.context['product'] = product
            self.context['invoice_paid'] = invoice_paid

        elif offer['type'] == Order.TWO_PAYMENTS_ORDER:

            price = stripe.Price.create(
                unit_amount=int(unit_amount_with_discount * 100),
                currency=user.currency,
                product=product['id']
            )
            stripe.InvoiceItem.create(
                customer=user.stripe_customer_id,
                price=price['id'],
            )
            invoice = stripe.Invoice.create(
                customer=user.stripe_customer_id,
                default_payment_method=payment_method_id

            )
            user.default_payment_method = payment_method_id
            user.save()
            invoice_paid = stripe.Invoice.pay(invoice['id'])
            self.context['price'] = price
            self.context['product'] = product

            self.context['invoice_paid'] = invoice_paid
        elif offer['type'] == Order.RECURRENT_ORDER:
            if not 'interval_subscription' in offer:
                raise serializers.ValidationError(
                    "Not interval subscription in offer")
            switcher = {
                Order.MONTH: "month",
                Order.YEAR: "year"
            }
            interval = switcher.get(offer['interval_subscription'], None)
            if not interval:
                raise serializers.ValidationError(
                    "Interval not valid")
            user.default_payment_method = payment_method_id
            user.save()
            price = stripe.Price.create(
                unit_amount=int(unit_amount_with_discount * 100),
                currency=user.currency,
                recurring={"interval": interval},
                product=product['id']
            )
            self.context['product'] = product

            self.context['price'] = price

        else:
            raise serializers.ValidationError(
                "Not a valid order type")

        return data

    def create(self, validated_data):
        offer = self.context['offer']
        request = self.context['request']
        user = request.user
        stripe = self.context['stripe']
        product = self.context['product']

        offer_object = self.context['offer_object']

        service_fee, _ = helpers.convert_currency('USD', user.currency, offer['service_fee'], offer_object.rate_date)
        unit_amount, _ = helpers.convert_currency('USD', user.currency, offer['unit_amount'], offer_object.rate_date)
        used_credits, _ = helpers.convert_currency("USD", user.currency, offer['used_credits'], offer_object.rate_date)

        new_order = Order.objects.create(
            offer=offer_object,
            buyer=offer_object.buyer,
            seller=offer_object.seller,
            title=offer_object.title,
            description=offer_object.description,
            unit_amount=unit_amount,
            used_credits=used_credits,
            service_fee=service_fee,
            first_payment=offer_object.first_payment,
            payment_at_delivery=offer_object.payment_at_delivery,
            delivery_date=offer_object.delivery_date,
            delivery_time=offer_object.delivery_time,
            interval_subscription=offer_object.interval_subscription,
            type=offer_object.type,
            rate_date=offer_object.rate_date,
            product_id=product['id']
        )

        offer_activity_queryset = OfferActivity.objects.filter(offer=offer_object, status=OfferActivity.PENDENDT)
        offer_activity = None
        if offer_activity_queryset.exists():
            offer_activity = offer_activity_queryset.first()
        activity = offer_activity.activity
        activity.closed = True
        activity.active = False
        activity = Activity.objects.create(
            type=Activity.OFFER,
            order=new_order,
            closed=True,
            active=False
        )
        OfferActivity.objects.create(
            activity=activity,
            offer=offer_object,
            status=OfferActivity.ACCEPTED
        )

        chats = Chat.objects.filter(participants=new_order.seller)
        chats = chats.filter(participants=new_order.buyer)
        chat_instance = None
        if chats.exists():
            for chat in chats:
                if chat.participants.all().count() == 2:
                    chat_instance = chat

        if not chat_instance:

            chat_instance = Chat.objects.create()

            chat_instance.participants.add(new_order.buyer)
            chat_instance.participants.add(new_order.seller)
            chat_instance.save()

        # Create the message

        message = Message.objects.create(chat=chat_instance, activity=activity, sent_by=new_order.buyer)
        chat_instance.last_message = message
        chat_instance.save()

        # Set message seen
        seen_by, _ = SeenBy.objects.get_or_create(chat=chat_instance, user=new_order.buyer)
        if seen_by.message != chat_instance.last_message:

            seen_by.message = chat_instance.last_message
            seen_by.save()

        if offer['type'] == Order.ONE_PAYMENT_ORDER:
            price = self.context['price']

            # user.available_for_withdrawal = user.available_for_withdrawal - \
            #     Money(amount=used_credits, currency="USD")
            if used_credits:

                Earning.objects.create(
                    user=user,
                    type=Earning.SPENT,
                    amount=Money(amount=used_credits, currency="USD")
                )

                # Substract in pending_clearance and available_for_withdrawal the used credits amount

                pending_clearance = user.pending_clearance - Money(amount=used_credits, currency="USD")

                if pending_clearance < Money(amount=0, currency="USD"):
                    user.pending_clearance = Money(amount=0, currency="USD")
                    available_money_payed = abs(pending_clearance)
                    available_for_withdrawal = user.available_for_withdrawal - available_money_payed
                    if available_for_withdrawal < Money(amount=0, currency="USD"):
                        available_for_withdrawal = Money(amount=0, currency="USD")
                    user.available_for_withdrawal = available_for_withdrawal
                else:
                    user.pending_clearance = pending_clearance

                user.used_for_purchases = user.used_for_purchases + Money(amount=used_credits, currency="USD")
                user.save()

            invoice_paid = self.context['invoice_paid']
            invoice_id = invoice_paid['id']
            currency = invoice_paid['currency']
            charge_id = invoice_paid['charge']
            amount_paid = invoice_paid['amount_paid']
            status = invoice_paid['status']
            invoice_pdf = invoice_paid['invoice_pdf']

            new_order.price_id = price['id']
            new_order.save()

            OrderPayment.objects.create(
                order=new_order,
                invoice_id=invoice_id,
                invoice_pdf=invoice_pdf,
                charge_id=charge_id,
                amount_paid=float(amount_paid) / 100,
                currency=currency,
                status=status,
            )

            seller = new_order.seller
            seller.net_income = seller.net_income + offer_object.unit_amount
            seller.save()
            Earning.objects.create(
                user=seller,
                amount=offer_object.unit_amount,
                available_for_withdrawn_date=timezone.now() + timedelta(days=14)
            )
            seller.pending_clearance += offer_object.unit_amount

        elif offer['type'] == Order.HOLDING_PAYMENT_ORDER:

            # user.available_for_withdrawal = user.available_for_withdrawal - \
            #     Money(amount=used_credits, currency="USD")

            if used_credits > 0:
                Earning.objects.create(
                    user=user,
                    type=Earning.SPENT,
                    amount=Money(amount=used_credits, currency="USD")
                )

                # Substract in pending_clearance and available_for_withdrawal the used credits amount
                pending_clearance = user.pending_clearance - Money(amount=used_credits, currency="USD")

                if pending_clearance < Money(amount=0, currency="USD"):
                    user.pending_clearance = Money(amount=0, currency="USD")
                    available_money_payed = abs(pending_clearance)
                    available_for_withdrawal = user.available_for_withdrawal - available_money_payed
                    if available_for_withdrawal < Money(amount=0, currency="USD"):
                        available_for_withdrawal = Money(amount=0, currency="USD")
                    user.available_for_withdrawal = available_for_withdrawal
                else:

                    user.pending_clearance = pending_clearance
                user.used_for_purchases += Money(amount=used_credits, currency="USD")
                user.save()

            price = self.context['price']

            invoice_paid = self.context['invoice_paid']
            invoice_id = invoice_paid['id']
            currency = invoice_paid['currency']
            charge_id = invoice_paid['charge']
            amount_paid = invoice_paid['amount_paid']
            status = invoice_paid['status']
            invoice_pdf = invoice_paid['invoice_pdf']

            new_order.price_id = price['id']
            new_order.due_to_seller = offer_object.unit_amount
            new_order.save()

            OrderPayment.objects.create(
                order=new_order,
                invoice_id=invoice_id,
                invoice_pdf=invoice_pdf,
                charge_id=charge_id,
                amount_paid=float(amount_paid) / 100,
                currency=currency,
                status=status,
            )

        elif offer['type'] == Order.TWO_PAYMENTS_ORDER:
            price = self.context['price']

            # user.available_for_withdrawal = user.available_for_withdrawal - \
            #     Money(amount=used_credits, currency="USD")
            if used_credits:

                Earning.objects.create(
                    user=user,
                    type=Earning.SPENT,
                    amount=Money(amount=used_credits, currency="USD")
                )

                # Substract in pending_clearance and available_for_withdrawal the used credits amount

                pending_clearance = user.pending_clearance - Money(amount=used_credits, currency="USD")

                if pending_clearance < Money(amount=0, currency="USD"):
                    user.pending_clearance = Money(amount=0, currency="USD")
                    available_money_payed = abs(pending_clearance)
                    available_for_withdrawal = user.available_for_withdrawal - available_money_payed
                    if available_for_withdrawal < Money(amount=0, currency="USD"):
                        available_for_withdrawal = Money(amount=0, currency="USD")
                    user.available_for_withdrawal = available_for_withdrawal
                else:
                    user.pending_clearance = pending_clearance

                user.used_for_purchases = user.used_for_purchases + Money(amount=used_credits, currency="USD")
                user.save()

            invoice_paid = self.context['invoice_paid']
            invoice_id = invoice_paid['id']
            currency = invoice_paid['currency']
            charge_id = invoice_paid['charge']
            amount_paid = invoice_paid['amount_paid']
            status = invoice_paid['status']
            invoice_pdf = invoice_paid['invoice_pdf']

            new_order.price_id = price['id']
            new_order.payment_at_delivery = offer_object.payment_at_delivery
            new_order.save()

            OrderPayment.objects.create(
                order=new_order,
                invoice_id=invoice_id,
                invoice_pdf=invoice_pdf,
                charge_id=charge_id,
                amount_paid=float(amount_paid) / 100,
                currency=currency,
                status=status,
            )

            seller = new_order.seller
            seller.net_income = seller.net_income + offer_object.first_payment
            seller.save()
            Earning.objects.create(
                user=seller,
                amount=offer_object.first_payment,
                available_for_withdrawn_date=timezone.now() + timedelta(days=14)
            )
            seller.pending_clearance += offer_object.first_payment

        elif offer['type'] == Order.RECURRENT_ORDER:
            price = self.context['price']
            try:
                subscription = stripe.Subscription.create(
                    customer=user.stripe_customer_id,
                    items=[
                        {"price": price['id']}
                    ],
                    expand=["latest_invoice.payment_intent"],
                )
                subscription_id = subscription['id']

                new_order.price_id = price['id']
                new_order.subscription_id = subscription_id
                new_order.save()

            except Exception as e:
                new_order.delete()
                offer_object.save()
                print(e)
                raise serializers.ValidationError(
                    'Something went wrong')
        offer_object.accepted = True
        offer_object.save()
        new_order.seller.active_month = True
        new_order.seller.save()
        return new_order
