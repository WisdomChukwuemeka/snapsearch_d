from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ShipmentTracking, TrackingEvent


class UserShipmentsView(APIView):
    """List all shipments for the logged-in user."""
    def get(self, request):
        shipments = ShipmentTracking.objects.filter(user=request.user, is_visible_to_user=True)
        return Response({"shipments": [_serialize_shipment(s) for s in shipments]})


class TrackShipmentView(APIView):
    """Lookup a single shipment by tracking ID."""
    def get(self, request, tracking_id):
        try:
            shipment = ShipmentTracking.objects.get(
                tracking_id=tracking_id, user=request.user, is_visible_to_user=True
            )
        except ShipmentTracking.DoesNotExist:
            return Response({"error": "Tracking ID not found or not associated with your account."}, status=404)
        return Response(_serialize_shipment(shipment, include_events=True))


def _serialize_shipment(s, include_events=False):
    data = {
        "tracking_id":        s.tracking_id,
        "order_reference":    s.order_reference,
        "product_name":       s.product_name,
        "product_image":      s.product_image,
        "supplier_name":      s.supplier_name,
        "supplier_platform":  s.supplier_platform,
        "carrier":            s.carrier,
        "carrier_tracking_url": s.carrier_tracking_url,
        "origin_country":     s.origin_country,
        "status":             s.status,
        "status_display":     s.get_status_display(),
        "order_date":         s.order_date.isoformat(),
        "shipped_at":         s.shipped_at.isoformat() if s.shipped_at else None,
        "estimated_delivery": s.estimated_delivery.isoformat() if s.estimated_delivery else None,
        "delivered_at":       s.delivered_at.isoformat() if s.delivered_at else None,
    }
    if include_events:
        data["events"] = [
            {"status": e.status, "location": e.location,
             "description": e.description, "timestamp": e.timestamp.isoformat()}
            for e in s.events.all()
        ]
    return data
