from django.core.management.base import BaseCommand
from api.plans.models import Plan


class Command(BaseCommand):

    def handle(self, *args, **options):

        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=12.50,
            currency="EUR",
            price_label="12.50€",
            stripe_price_id="price_1IblK3Dieqyg7vAIXvA5vo5C",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"

        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=14.90,
            currency="USD",
            price_label="$14.90",
            stripe_price_id="price_1IblK3Dieqyg7vAI9QpUYcT9",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=19.90,
            currency="AUD",
            price_label="$19.90",
            stripe_price_id="price_1IblK3Dieqyg7vAII9llSKGS",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=79.90,
            currency="BRL",
            price_label="R$79.90",
            stripe_price_id="price_1IblK3Dieqyg7vAIJEPn9g1X",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=18.90,
            currency="CAD",
            price_label="R$18.90",
            stripe_price_id="price_1IblK3Dieqyg7vAIQvMblME8",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=12.50,
            currency="GBP",
            price_label="£12.50",
            stripe_price_id="price_1IblK3Dieqyg7vAIQXbGWUyv",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=22000000.00,
            currency="IDR",
            price_label="Rp22000000.00",
            stripe_price_id="price_1IblK3Dieqyg7vAIh73MM1tn",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=49.90,
            currency="ILS",
            price_label="₪49.90",
            stripe_price_id="price_1IblK3Dieqyg7vAIXpoCI7Bl",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=1100.00,
            currency="INR",
            price_label="₹1100.00",
            stripe_price_id="price_1IblK3Dieqyg7vAI25tCzhCJ",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=1700.00,
            currency="JPY",
            price_label="¥1700.00",
            stripe_price_id="price_1IblK3Dieqyg7vAITc3HZWvv",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=1700000.00,
            currency="KRW",
            price_label="₩1700000.00",
            stripe_price_id="price_1IblK3Dieqyg7vAIXvA5vo5C",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=300.00,
            currency="MXN",
            price_label="$300.00",
            stripe_price_id="price_1IblK3Dieqyg7vAIyV1KeZId",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=130.00,
            currency="NOK",
            price_label="130.00kr",
            stripe_price_id="price_1IblK3Dieqyg7vAIOMU59hfC",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=59.90,
            currency="PLN",
            price_label="59.90zł",
            stripe_price_id="price_1IblK3Dieqyg7vAIs1MUtTVS",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=1100.00,
            currency="RUB",
            price_label="₽1100.00",
            stripe_price_id="price_1IblK3Dieqyg7vAIu6IP2gtc",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=19.90,
            currency="SGD",
            price_label="$19.90",
            stripe_price_id="price_1IblK3Dieqyg7vAIKLAiwSiR",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=460.00,
            currency="THB",
            price_label="฿460.00",
            stripe_price_id="price_1IblK3Dieqyg7vAIwUd6quwH",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=109.00,
            currency="TRY",
            price_label="₺109.00",
            stripe_price_id="price_1IblK3Dieqyg7vAIWFmT8OjF",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=425.00,
            currency="TWD",
            price_label="₺425.00",
            stripe_price_id="price_1IblK2Dieqyg7vAIBqyPpBhJ",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=219.00,
            currency="ZAR",
            price_label="₺219.00",
            stripe_price_id="price_1IblK2Dieqyg7vAIpDVMvv4n",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=2300.00,
            currency="PKR",
            price_label="₨2300.00",
            stripe_price_id="price_1IblK2Dieqyg7vAIgJtewxXN",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=100.00,
            currency="CNY",
            price_label="¥100.00",
            stripe_price_id="price_1IblK2Dieqyg7vAIJmzVZZbB",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=60.00,
            currency="SAR",
            price_label="SR60.00",
            stripe_price_id="price_1IblK2Dieqyg7vAIB9bPDh0x",
            stripe_product_id="prod_JEDl98Ujc9Gwd8"


        )
        print("Plans created")
