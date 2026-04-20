from django.contrib import admin
from .models import GeminiSearchHistory


@admin.register(GeminiSearchHistory)
class GeminiSearchHistoryAdmin(admin.ModelAdmin):
    list_display    = ("user", "product_name", "product_category", "query_type",
                       "ai_provider", "tokens_used", "was_free", "created_at")
    list_filter     = ("query_type", "ai_provider", "was_free")
    search_fields   = ("user__username", "user__email", "product_name", "product_category")
    readonly_fields = ("created_at",)
    date_hierarchy  = "created_at"

    def has_add_permission(self, request):
        return False   # records are created programmatically only