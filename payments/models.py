from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ("pending",  "Pending"),
        ("success",  "Success"),
        ("failed",   "Failed"),
        ("refunded", "Refunded"),
    ]

    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_transactions")
    reference          = models.CharField(max_length=120, unique=True, db_index=True)
    amount_naira       = models.DecimalField(max_digits=10, decimal_places=2)
    tokens_purchased   = models.IntegerField(default=2)
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    # Paystack metadata
    paystack_reference = models.CharField(max_length=200, blank=True)
    channel            = models.CharField(max_length=50, blank=True)   # card / bank_transfer / ussd
    card_last4         = models.CharField(max_length=4, blank=True)
    bank_name          = models.CharField(max_length=100, blank=True)
    paystack_response  = models.JSONField(null=True, blank=True)
    # Timestamps
    initiated_at       = models.DateTimeField(auto_now_add=True)
    completed_at       = models.DateTimeField(null=True, blank=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-initiated_at"]
        verbose_name = "Payment Transaction"

    def __str__(self):
        return f"{self.user.username} | ₦{self.amount_naira} | {self.status} | {self.reference}"


class Commission(models.Model):
    """Records affiliate commission earned when a user clicks a buy link."""
    STATUS_CHOICES = [
        ("clicked",   "Link Clicked"),
        ("confirmed", "Purchase Confirmed"),
        ("paid",      "Commission Paid"),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commissions")
    platform       = models.CharField(max_length=50)       # amazon / aliexpress / ebay
    product_name   = models.CharField(max_length=300)
    affiliate_url  = models.URLField(max_length=800)
    commission_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    estimated_usd  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default="clicked")
    clicked_at     = models.DateTimeField(auto_now_add=True)
    confirmed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-clicked_at"]

    def __str__(self):
        return f"{self.user.username} | {self.platform} | {self.product_name} | {self.status}"
