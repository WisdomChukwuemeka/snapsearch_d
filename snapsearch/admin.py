from django.contrib import admin
from django.utils.html import format_html
from .models import SearchHistory


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display   = ("user", "product_name", "product_category",
                      "query_type", "tokens_used", "was_free", "image_preview", "created_at")
    list_filter    = ("query_type", "was_free")
    search_fields  = ("user__username", "user__email", "product_name", "product_category")
    readonly_fields = ("created_at", "image_preview")
    date_hierarchy  = "created_at"

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height:80px;border-radius:8px"/>', obj.image_url)
        return "No image"
    image_preview.short_description = "Product Image"
