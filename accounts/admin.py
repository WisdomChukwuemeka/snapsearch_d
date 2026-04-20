from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# Unregister default and re-register with extra info
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name",
                    "is_staff", "date_joined", "token_balance_display", "total_searches_display")

    def token_balance_display(self, obj):
        try:
            return f"💎 {obj.token_balance.tokens}"
        except Exception:
            return "—"
    token_balance_display.short_description = "Tokens"

    def total_searches_display(self, obj):
        try:
            return obj.token_balance.total_searches
        except Exception:
            return "—"
    total_searches_display.short_description = "Searches"
