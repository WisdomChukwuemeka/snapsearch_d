from django.contrib import admin
from .models import TokenPricing, UserTokenBalance


@admin.register(TokenPricing)
class TokenPricingAdmin(admin.ModelAdmin):
    list_display  = ("label", "tokens_per_pack", "price_naira", "is_active", "updated_at")
    list_editable = ("price_naira", "tokens_per_pack", "is_active")
    readonly_fields = ("updated_at",)

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserTokenBalance)
class UserTokenBalanceAdmin(admin.ModelAdmin):
    list_display   = ("user", "tokens", "is_first_search", "total_searches", "total_tokens_bought", "updated_at")
    search_fields  = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    list_filter    = ("is_first_search",)
