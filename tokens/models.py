from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TokenPricing(models.Model):
    """Configurable token pricing — editable from Django admin."""
    tokens_per_pack   = models.IntegerField(default=2)
    price_naira       = models.DecimalField(max_digits=10, decimal_places=2, default=200.00)
    is_active         = models.BooleanField(default=True)
    label             = models.CharField(max_length=100, default="Standard Pack")
    updated_at        = models.DateTimeField(auto_now=True)
    updated_by        = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "Token Pricing"
        verbose_name_plural = "Token Pricing"

    def __str__(self):
        return f"{self.label} — ₦{self.price_naira} / {self.tokens_per_pack} tokens"


class UserTokenBalance(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name="token_balance")
    tokens           = models.IntegerField(default=0)
    is_first_search  = models.BooleanField(default=True)
    total_searches   = models.IntegerField(default=0)
    total_tokens_bought = models.IntegerField(default=0)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.tokens} tokens"

    def can_search(self):
        return self.is_first_search or self.tokens >= 2

    def consume_tokens(self):
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
        self.total_tokens_bought += amount
        self.save()
