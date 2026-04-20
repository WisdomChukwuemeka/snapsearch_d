from django.contrib import admin
from django.utils.html import format_html
from .models import ShipmentTracking, TrackingEvent


class TrackingEventInline(admin.TabularInline):
    model   = TrackingEvent
    extra   = 1
    fields  = ("timestamp", "status", "location", "description")
    ordering = ("-timestamp",)


@admin.register(ShipmentTracking)
class ShipmentTrackingAdmin(admin.ModelAdmin):
    list_display   = ("tracking_id", "status", "user", "product_name", "supplier_name",
                      "status_badge", "carrier", "order_date", "estimated_delivery", "delivered_at")
    list_filter    = ("status", "supplier_platform", "carrier")
    search_fields  = ("tracking_id", "user__username", "user__email",
                      "product_name", "supplier_name", "order_reference")
    readonly_fields = ("order_date", "updated_at", "product_image_preview")
    date_hierarchy  = "order_date"
    inlines         = [TrackingEventInline]
    list_editable   = ("status",)

    fieldsets = (
        ("Shipment Info", {
            "fields": ("user", "tracking_id", "order_reference", "product_name",
                       "product_image", "product_image_preview")
        }),
        ("Supplier", {
            "fields": ("supplier_name", "supplier_platform", "origin_country")
        }),
        ("Carrier", {
            "fields": ("carrier", "carrier_tracking_url")
        }),
        ("Status & Dates", {
            "fields": ("status", "order_date", "shipped_at", "estimated_delivery",
                       "delivered_at", "updated_at")
        }),
        ("Settings", {
            "fields": ("destination_address", "admin_notes", "is_visible_to_user")
        }),
    )

    def status_badge(self, obj):
        colors = {
            "order_placed":      "#6ea8fe",
            "processing":        "#e8c547",
            "shipped":           "#c47a47",
            "in_transit":        "#a47ae8",
            "out_for_delivery":  "#e8a547",
            "delivered":         "#47c47a",
            "exception":         "#e85447",
            "returned":          "#888880",
        }
        color = colors.get(obj.status, "#888")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def product_image_preview(self, obj):
        if obj.product_image:
            return format_html('<img src="{}" style="max-height:120px;border-radius:8px"/>', obj.product_image)
        return "No image"
    product_image_preview.short_description = "Image Preview"


@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display  = ("shipment", "status", "location", "timestamp")
    list_filter   = ("status",)
    search_fields = ("shipment__tracking_id", "location", "description")
    date_hierarchy = "timestamp"
