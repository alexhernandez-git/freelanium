
"""Invitations tests."""

# Django
import pdb
from django.test import TestCase

# Django REST Framework
from rest_framework import status
from rest_framework.test import APITestCase

# Model
from api.users.models import User, Earning
from api.orders.models import Order, OrderPayment
from djmoney.money import Money
from rest_framework.authtoken.models import Token

# Utils
import stripe
from api.utils import helpers
from django.utils import timezone
from datetime import timedelta

# Tests
from api.users.tests.register_test import SetupUsersInitialData


class RecurrentOrderAPITestCase(SetupUsersInitialData):

    def setUp(self):
        super().setUp()
        stripe.api_key = 'sk_test_51IZy28Dieqyg7vAImOKb5hg7amYYGSzPTtSqoT9RKI69VyycnqXV3wCPANyYHEl2hI7KLHHAeIPpC7POg7I4WMwi00TSn067f4'
        self.stripe = stripe

        # In dollars
        buyer = User.objects.get(id=self.buyer['id'])

        self.net_income = 75
        self.available_for_withdrawal = 20
        self.pending_clearance = 0
        buyer.net_income = self.net_income
        buyer.available_for_withdrawal = self.available_for_withdrawal
        buyer.pending_clearance = self.pending_clearance

        buyer.save()
        self.create_offer()

        self.accept_offer()

        self.seller_recieve_subscription_payment()

    def create_offer(self):
        order_usd_price = 25
        offer_data = {
            "buyer": self.buyer['id'],
            "buyer_email": "",
            "delivery_time": "7",
            "send_offer_by_email": False,
            "title": "Holding payment order",
            "description": "Holding payment order offer",
            "type": "RO",
            "unit_amount": str(order_usd_price)
        }
        self.order_usd_price = order_usd_price

        self.client.credentials(HTTP_AUTHORIZATION="Token {}".format(self.seller_token))

        create_offer_response = self.client.post("/api/offers/", offer_data)
        self.create_offer_response = create_offer_response
        self.offer = create_offer_response.data

    def accept_offer(self):
        # Convert the offer in buyer currency
        offer = self.offer
        buyer = User.objects.get(id=self.buyer['id'])

        currencyRate, _ = helpers.get_currency_rate(buyer.currency, offer['rate_date'])
        subtotal = float(offer['unit_amount']) * currencyRate

        available_for_withdrawal = (float(buyer.available_for_withdrawal.amount) +
                                    float(buyer.pending_clearance.amount)) * currencyRate
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
        offer['subtotal'] = round(subtotal, 2)
        offer['service_fee'] = round(service_fee, 2)
        offer['unit_amount'] = round(unit_amount, 2)
        offer['used_credits'] = round(used_credits, 2)

        # Petition data

        # Get the payment method id
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 3,
                "exp_year": 2022,
                "cvc": "314",
            },
        )

        # Attach payment method
        self.client.credentials(HTTP_AUTHORIZATION="Token {}".format(self.buyer_token))

        attach_payment_method_data = {
            "payment_method_id": payment_method['id'],
            "card_name": "Ivan Herms"
        }
        attach_payment_method_response = self.client.patch(
            "/api/users/attach_payment_method/", attach_payment_method_data, format='json')
        self.attach_payment_method_response = attach_payment_method_response

        # Send accepting offer
        order_data = {
            "offer": offer,
            "payment_method_id": payment_method['id']
        }

        accept_order_response = self.client.post("/api/orders/", order_data, format='json')
        self.accept_order_response = accept_order_response
        self.order = accept_order_response.data

    def seller_recieve_subscription_payment(self):
        order = Order.objects.get(id=self.order['id'])

        # Set a amount of credits reserved for this order for testing propouses
        subscription_id = order.subscription_id

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
                else:
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

    def test_is_offer_created(self):
        self.assertEqual(self.create_offer_response.status_code, status.HTTP_201_CREATED)

    def test_if_payment_method_has_been_attached(self):
        self.assertEqual(self.attach_payment_method_response.status_code, status.HTTP_200_OK)

    def test_is_offer_accepted(self):
        self.assertEqual(self.accept_order_response.status_code, status.HTTP_201_CREATED)

    # def test_seller_earned_what_expected(self):
    #     seller = User.objects.get(id=self.seller['id'])
    #     order = Order.objects.get(id=self.order['id'])
    #     expected_earnings = order.offer.unit_amount
    #     actually_earned = seller.pending_clearance
    #     self.assertEqual(expected_earnings, actually_earned)

    # def test_buyer_spent_what_expected(self):
    #     buyer = User.objects.get(id=self.buyer['id'])
    #     order_price = float(self.order_usd_price)
    #     order = Order.objects.get(id=self.order['id'])
    #     available_for_withdrawal = self.available_for_withdrawal
    #     pending_clearance = self.pending_clearance

    #     pending_clearance -= order_price
    #     if pending_clearance < 0:
    #         substract_available_for_withdrawal = abs(pending_clearance)
    #         pending_clearance = 0
    #         available_for_withdrawal -= substract_available_for_withdrawal
    #         if available_for_withdrawal < 0:
    #             available_for_withdrawal = 0

    #     self.assertEqual(available_for_withdrawal, buyer.available_for_withdrawal.amount)
    #     self.assertEqual(pending_clearance, buyer.pending_clearance.amount)
