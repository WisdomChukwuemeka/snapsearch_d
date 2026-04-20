from django.contrib import admin
from .models import PaymentTransaction, Commission


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display   = ("reference", "user", "amount_naira", "tokens_purchased",
                      "status", "channel", "bank_name", "initiated_at", "completed_at")
    list_filter    = ("status", "channel")
    search_fields  = ("reference", "user__username", "user__email", "bank_name")
    readonly_fields = ("reference", "paystack_reference", "paystack_response",
                       "initiated_at", "completed_at", "updated_at")
    date_hierarchy = "initiated_at"

    def has_add_permission(self, request):
        return False  # Payments are created programmatically only


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display  = ("user", "platform", "product_name", "commission_pct",
                     "estimated_usd", "status", "clicked_at")
    list_filter   = ("platform", "status")
    search_fields = ("user__username", "product_name", "platform")
    readonly_fields = ("clicked_at", "confirmed_at")
    date_hierarchy  = "clicked_at"
