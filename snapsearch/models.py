from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class SearchHistory(models.Model):
    QUERY_TYPES = [
        ("buy",    "Buy"),
        ("learn",  "Learn"),
        ("others", "Others"),
    ]

    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name="searches")
    product_name     = models.CharField(max_length=500, blank=True)
    product_category = models.CharField(max_length=200, blank=True)
    query_type       = models.CharField(max_length=20, choices=QUERY_TYPES)
    image_url        = models.URLField(max_length=800, blank=True)   # stored product image URL
    tokens_used      = models.IntegerField(default=2)
    was_free         = models.BooleanField(default=False)
    result_summary   = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Search History"
        verbose_name_plural = "Search History"

    def __str__(self):
        return f"{self.user.username} — {self.product_name} — {self.query_type}"
