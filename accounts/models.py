from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class UserTokenBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="accounts_token_balance")
    tokens = models.IntegerField(default=0)
    is_first_search = models.BooleanField(default=True)
    total_searches = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.tokens} tokens"

    def can_search(self):
        """Returns True if user can perform a search (first search free OR has 2+ tokens)."""
        return self.is_first_search or self.tokens >= 2

    def consume_tokens(self):
        """Deducts tokens for a search. Returns True if successful."""
        if self.is_first_search:
            self.is_first_search = False
            self.total_searches += 1
            self.save()
            return True
        if self.tokens >= 2:
            self.tokens -= 2
            self.total_searches += 1
            self.save()
            return True
        return False

    def add_tokens(self, amount):
        self.tokens += amount
        self.save()


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="accounts_transactions")
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # In Naira
    tokens_purchased = models.IntegerField(default=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    paystack_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.reference} — {self.status}"
