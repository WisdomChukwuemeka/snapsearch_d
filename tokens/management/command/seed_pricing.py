from django.core.management.base import BaseCommand
from tokens.models import TokenPricing

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        packs = [
            {"label": "Starter Pack", "tokens_per_pack": 2, "price_naira": 200},
            {"label": "Value Pack", "tokens_per_pack": 10, "price_naira": 800},
            {"label": "Pro Pack", "tokens_per_pack": 30, "price_naira": 2000},
            {"label": "Power Pack", "tokens_per_pack": 100, "price_naira": 6000},
        ]

        for pack in packs:
            TokenPricing.objects.update_or_create(
                label=pack["label"],
                defaults={
                    "tokens_per_pack": pack["tokens_per_pack"],
                    "price_naira": pack["price_naira"],
                    "is_active": True
                }
            )

        self.stdout.write(self.style.SUCCESS("Pricing seeded successfully"))