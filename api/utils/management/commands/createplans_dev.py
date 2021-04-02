from django.core.management.base import BaseCommand
from api.plans.models import Plan


class Command(BaseCommand):

    def handle(self, *args, **options):

        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=12.50,
            currency="EUR",
            price_label="12.50€",
            stripe_price_id="price_1IblHZDieqyg7vAI7OPVg52R",
            stripe_product_id="prod_JEDjYAV0Z42eWv"

        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=14.90,
            currency="USD",
            price_label="$14.90",
            stripe_price_id="price_1IblHZDieqyg7vAI1Kws4AJK",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=19.90,
            currency="AUD",
            price_label="$19.90",
            stripe_price_id="price_1IblHZDieqyg7vAILelPEgcA",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=79.90,
            currency="BRL",
            price_label="R$79.90",
            stripe_price_id="price_1IblHZDieqyg7vAIlFIUSUTa",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=18.90,
            currency="CAD",
            price_label="R$18.90",
            stripe_price_id="price_1IblHZDieqyg7vAICI5QK6tk",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=12.50,
            currency="GBP",
            price_label="£12.50",
            stripe_price_id="price_1IblHZDieqyg7vAIkfFKftte",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=22000000.00,
            currency="IDR",
            price_label="Rp22000000.00",
            stripe_price_id="price_1IblHZDieqyg7vAI52W3lJKg",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=49.90,
            currency="ILS",
            price_label="₪49.90",
            stripe_price_id="price_1IblHZDieqyg7vAIWc4uNN6X",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=1100.00,
            currency="INR",
            price_label="₹1100.00",
            stripe_price_id="price_1IblHZDieqyg7vAIN8wq33xW",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=1700.00,
            currency="JPY",
            price_label="¥1700.00",
            stripe_price_id="price_1IblHZDieqyg7vAIQDnOSdbm",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=1700000.00,
            currency="KRW",
            price_label="₩1700000.00",
            stripe_price_id="price_1IblHaDieqyg7vAItjkdZjGH",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=300.00,
            currency="MXN",
            price_label="$300.00",
            stripe_price_id="price_1IblHZDieqyg7vAIvMYjPhri",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=130.00,
            currency="NOK",
            price_label="130.00kr",
            stripe_price_id="price_1IblHZDieqyg7vAI8Sv0535j",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=59.90,
            currency="PLN",
            price_label="59.90zł",
            stripe_price_id="price_1IblHZDieqyg7vAIalPARtcN",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=1100.00,
            currency="RUB",
            price_label="₽1100.00",
            stripe_price_id="price_1IblHZDieqyg7vAI9abOmkxq",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=19.90,
            currency="SGD",
            price_label="$19.90",
            stripe_price_id="price_1IblHZDieqyg7vAIXbx05uoe",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=460.00,
            currency="THB",
            price_label="฿460.00",
            stripe_price_id="price_1IblHaDieqyg7vAIGOMglv0a",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=109.00,
            currency="TRY",
            price_label="₺109.00",
            stripe_price_id="price_1IblHaDieqyg7vAIkcBhUcwe",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=425.00,
            currency="TWD",
            price_label="₺425.00",
            stripe_price_id="price_1IblHaDieqyg7vAIE2c2nixu",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=219.00,
            currency="ZAR",
            price_label="₺219.00",
            stripe_price_id="price_1IblHaDieqyg7vAIRpY0GbFd",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=2300.00,
            currency="PKR",
            price_label="₨2300.00",
            stripe_price_id="price_1IblHaDieqyg7vAIcU4iRDmR",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=100.00,
            currency="CNY",
            price_label="¥100.00",
            stripe_price_id="price_1IblHaDieqyg7vAIhOWtBLlK",
            stripe_product_id="prod_JEDjYAV0Z42eWv"


        )
        Plan.objects.create(
            type=Plan.BASIC,
            unit_amount=60.00,
            currency="SAR",
            price_label="SR60.00",
            stripe_price_id="price_1IblHaDieqyg7vAIVbEfbkIG",
            stripe_product_id="prod_JEDjYAV0Z42eWv"

        )
        print("Plans created")
