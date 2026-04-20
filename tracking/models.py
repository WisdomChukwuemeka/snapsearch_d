from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ShipmentTracking(models.Model):
    STATUS_CHOICES = [
        ("order_placed",   "Order Placed"),
        ("processing",     "Processing"),
        ("shipped",        "Shipped"),
        ("in_transit",     "In Transit"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered",      "Delivered"),
        ("exception",      "Exception / Held"),
        ("returned",       "Returned"),
    ]

    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shipments")
    tracking_id     = models.CharField(max_length=100, unique=True, db_index=True)
    order_reference = models.CharField(max_length=200, blank=True)   # supplier order ID
    product_name    = models.CharField(max_length=300)
    product_image   = models.URLField(max_length=800, blank=True)
    supplier_name   = models.CharField(max_length=200)
    supplier_platform = models.CharField(max_length=50, blank=True)  # amazon / aliexpress / ebay
    # Carrier
    carrier         = models.CharField(max_length=100, blank=True)   # DHL / FedEx / USPS etc
    carrier_tracking_url = models.URLField(max_length=800, blank=True)
    # Addresses
    origin_country  = models.CharField(max_length=100, blank=True)
    destination_address = models.TextField(blank=True)
    # Status
    status          = models.CharField(max_length=30, choices=STATUS_CHOICES, default="order_placed")
    # Timestamps
    order_date      = models.DateTimeField(auto_now_add=True)
    shipped_at      = models.DateTimeField(null=True, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    delivered_at    = models.DateTimeField(null=True, blank=True)
    updated_at      = models.DateTimeField(auto_now=True)
    # Admin notes
    admin_notes     = models.TextField(blank=True)
    is_visible_to_user = models.BooleanField(default=True)

    class Meta:
        ordering = ["-order_date"]
        verbose_name = "Shipment Tracking"

    def __str__(self):
        return f"{self.tracking_id} | {self.user.username} | {self.product_name} | {self.status}"


class TrackingEvent(models.Model):
    """Timeline events for a shipment."""
    shipment    = models.ForeignKey(ShipmentTracking, on_delete=models.CASCADE, related_name="events")
    status      = models.CharField(max_length=50)
    location    = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    timestamp   = models.DateTimeField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.shipment.tracking_id} | {self.status} @ {self.location}"
