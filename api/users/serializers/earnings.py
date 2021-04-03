
"""Users serializers."""

# Django REST Framework
from rest_framework import serializers

# Django
from django.conf import settings
from django.contrib.auth import password_validation, authenticate
from django.core.validators import RegexValidator
from django.shortcuts import get_object_or_404
from django.db.models import Sum

# Models
from api.users.models import Earning, User
from djmoney.models.fields import Money

# Utils

from paypalpayoutssdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment
from paypalpayoutssdk.payouts import PayoutsPostRequest
from paypalhttp import HttpError
from paypalhttp.encoder import Encoder
from paypalhttp.serializers.json_serializer import Json
from paypalpayoutssdk.payouts import PayoutsGetRequest

import random
import string

import environ
env = environ.Env()


class EarningModelSerializer(serializers.ModelSerializer):
    """User model serializer."""

    class Meta:
        """Meta class."""

        model = Earning
        fields = (
            "id",
            "type",
            "amount",
            "created",
            "available_for_withdrawn_date"
        )

        read_only_fields = ("id",)


class WithdrawFundsModelSerializer(serializers.ModelSerializer):
    """User model serializer."""

    class Meta:
        """Meta class."""

        model = Earning
        fields = (
            "id",
            "type",
            "amount",
            "created",
            "available_for_withdrawn_date"
        )

        read_only_fields = (
            "id",
            "type",
            "created",
            "available_for_withdrawn_date"
        )

    def validate(self, data):

        amount = Money(amount=data['amount'], currency="USD")
        request = self.context['request']
        user = request.user

        if amount > user.available_for_withdrawal:
            raise serializers.ValidationError('The amount is greater than your budget')
        if amount > Money(amount=5000, currency="USD"):
            raise serializers.ValidationError('The amount is too large')
        if not user.paypal_email:
            raise serializers.ValidationError('You don\'t have a PayPal account asociated')

        return data

    def create(self, validated_data):
        amount = Money(amount=validated_data['amount'], currency="USD")
        request = self.context['request']
        user = request.user

        # transfer = stripe.Transfer.create(
        #     amount=int(converted_unit_amount * 100),
        #     currency=user.currency,
        #     destination=user.stripe_account_id,
        # )
        # Creating Access Token for Sandbox

        if 'PAYPAL_CLIENT_ID' in env:
            client_id = env('PAYPAL_CLIENT_ID')
        else:
            client_id = "AbhmcP2IEj-X9YIyhPCeMApdZa8LiRaDFN8dCzG4OdMzrOuGPJC4hQ2KMvuNY7zWF-sxavTP-qmX9XWU"

        if 'PAYPAL_SECRET_KEY' in env:
            client_secret = env('PAYPAL_SECRET_KEY')
        else:
            client_secret = "EHkQZP9Qiw0G4EmmiPK2NS2qAOeG-rgp9_yq_h9kIWgdE9G__qq72OAwZNfFn3x8na2GX8F4lydn9XG2"

        # Creating an environment
        if 'PAYPAL_CLIENT_ID' in env and 'PAYPAL_SECRET_KEY' in env:

            environment = LiveEnvironment(client_id=client_id, client_secret=client_secret)
        else:
            environment = SandboxEnvironment(client_id=client_id, client_secret=client_secret)
        client = PayPalHttpClient(environment)
        senderBatchId = str(''.join(random.sample(
            string.ascii_uppercase + string.digits, k=7)))
        # Construct a request object and set desired parameters
        # Here, PayoutsPostRequest() creates a POST request to /v1/payments/payouts
        str_amount = str(validated_data['amount'])
        body = {
            "sender_batch_header": {
                "recipient_type": "EMAIL",
                "email_message": "SDK payouts test txn",
                "note": "Enjoy your Payout!!",
                "sender_batch_id": senderBatchId,
                "email_subject": "This is a test transaction from SDK"
            },
            "items": [{
                "note": "Your {}$ Payout!".format(str_amount),
                "amount": {
                    "currency": "USD",
                    "value": str_amount
                },
                "receiver": user.paypal_email,
                "sender_item_id": "Test_txn_1"
            }]
        }

        request = PayoutsPostRequest()
        request.request_body(body)

        try:
            # Call API with your client and get a response for your call
            response = client.execute(request)
            # If call returns body in response, you can get the deserialized version from the result attribute of the response
            batch_id = response.result.batch_header.payout_batch_id
            print(batch_id)

        except HttpError as httpe:
            # Handle server side API failure
            encoder = Encoder([Json()])
            error = encoder.deserialize_response(httpe.message, httpe.headers)
            print("Error: " + error["name"])
            print("Error message: " + error["message"])
            print("Information link: " + error["information_link"])
            print("Debug id: " + error["debug_id"])
            print("Details: ")
            if "details" in error:
                for detail in error["details"]:
                    print("Error location: " + detail["location"])
                    print("Error field: " + detail["field"])
                    print("Error issue: " + detail["issue"])
            raise serializers.ValidationError('Withdraw error')

        except IOError as ioe:
            # Handle cient side connection failures
            print(ioe.message)
            raise serializers.ValidationError('Withdraw error')

        # Here, PayoutsGetRequest() creates a GET request to /v1/payments/payouts/<batch-id>
        request = PayoutsGetRequest(batch_id)

        try:
            # Call API with your client and get a response for your call
            response = client.execute(request)

            # If call returns body in response, you can get the deserialized version from the result attribute of the response
            batch_status = response.result.batch_header.batch_status
            print(batch_status)
        except IOError as ioe:
            if isinstance(ioe, HttpError):
                # Something went wrong server-side
                print(ioe.status_code)
                print(ioe.headers)
                print(ioe)
            else:
                # Something went wrong client side
                print(ioe)
            raise serializers.ValidationError('Withdraw error')

        withdrawn = Earning.objects.create(
            type=Earning.WITHDRAWN,
            amount=amount,
            batch_id=batch_id,
            user=user
        )

        user.available_for_withdrawal -= amount
        user.withdrawn += amount
        user.save()

        return withdrawn
