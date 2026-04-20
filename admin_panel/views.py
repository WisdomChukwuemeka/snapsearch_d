from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from payments.models import PaymentTransaction, Commission
from tokens.models import UserTokenBalance, TokenPricing
from tracking.models import ShipmentTracking
from snapsearch.models import SearchHistory
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        now    = timezone.now()
        today  = now.date()
        week   = now - timedelta(days=7)
        month  = now - timedelta(days=30)

        # Revenue
        total_rev   = PaymentTransaction.objects.filter(status="success").aggregate(s=Sum("amount_naira"))["s"] or 0
        month_rev   = PaymentTransaction.objects.filter(status="success", completed_at__gte=month).aggregate(s=Sum("amount_naira"))["s"] or 0
        week_rev    = PaymentTransaction.objects.filter(status="success", completed_at__gte=week).aggregate(s=Sum("amount_naira"))["s"] or 0

        # Users
        total_users  = User.objects.count()
        new_this_week = User.objects.filter(date_joined__gte=week).count()

        # Searches
        total_searches = SearchHistory.objects.count()
        paid_searches  = SearchHistory.objects.filter(was_free=False).count()
        free_searches  = SearchHistory.objects.filter(was_free=True).count()

        # Commission
        total_comm  = Commission.objects.aggregate(s=Sum("estimated_usd"))["s"] or 0
        comm_clicks = Commission.objects.count()

        # Shipments
        active_ships = ShipmentTracking.objects.exclude(status__in=["delivered","returned"]).count()
        delivered    = ShipmentTracking.objects.filter(status="delivered").count()

        # Payment breakdown by channel
        channels = list(
            PaymentTransaction.objects.filter(status="success")
            .values("channel")
            .annotate(count=Count("id"), total=Sum("amount_naira"))
        )

        return Response({
            "revenue": {
                "total": float(total_rev),
                "this_month": float(month_rev),
                "this_week": float(week_rev),
            },
            "users": {
                "total": total_users,
                "new_this_week": new_this_week,
            },
            "searches": {
                "total": total_searches,
                "paid": paid_searches,
                "free": free_searches,
            },
            "commission": {
                "total_estimated_usd": float(total_comm),
                "total_clicks": comm_clicks,
            },
            "shipments": {
                "active": active_ships,
                "delivered": delivered,
            },
            "payment_channels": channels,
        })


class AdminPaymentsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get("status", "success")
        limit         = int(request.query_params.get("limit", 50))

        txns = PaymentTransaction.objects.filter(status=status_filter).select_related("user").order_by("-initiated_at")[:limit]
        return Response({"payments": [
            {
                "id":            t.id,
                "reference":     t.reference,
                "user":          t.user.username,
                "email":         t.user.email,
                "amount_naira":  str(t.amount_naira),
                "tokens":        t.tokens_purchased,
                "status":        t.status,
                "channel":       t.channel,
                "bank_name":     t.bank_name,
                "card_last4":    t.card_last4,
                "initiated_at":  t.initiated_at.isoformat(),
                "completed_at":  t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in txns
        ]})


class AdminSearchHistoryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        limit   = int(request.query_params.get("limit", 50))
        q_type  = request.query_params.get("query_type", "")
        searches = SearchHistory.objects.select_related("user").order_by("-created_at")
        if q_type:
            searches = searches.filter(query_type=q_type)
        searches = searches[:limit]
        return Response({"searches": [
            {
                "user":          s.user.username,
                "email":         s.user.email,
                "product_name":  s.product_name,
                "category":      s.product_category,
                "query_type":    s.query_type,
                "tokens_used":   s.tokens_used,
                "was_free":      s.was_free,
                "image_url":     s.image_url,
                "created_at":    s.created_at.isoformat(),
            }
            for s in searches
        ]})


class AdminCommissionView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        limit       = int(request.query_params.get("limit", 50))
        commissions = Commission.objects.select_related("user").order_by("-clicked_at")[:limit]
        return Response({"commissions": [
            {
                "user":           c.user.username,
                "platform":       c.platform,
                "product_name":   c.product_name,
                "commission_pct": str(c.commission_pct),
                "estimated_usd":  str(c.estimated_usd),
                "status":         c.status,
                "clicked_at":     c.clicked_at.isoformat(),
            }
            for c in commissions
        ]})


class AdminShipmentView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get("status", "")
        limit         = int(request.query_params.get("limit", 50))
        ships = ShipmentTracking.objects.select_related("user").order_by("-order_date")
        if status_filter:
            ships = ships.filter(status=status_filter)
        ships = ships[:limit]
        return Response({"shipments": [
            {
                "id":               s.id,
                "tracking_id":      s.tracking_id,
                "user":             s.user.username,
                "email":            s.user.email,
                "product_name":     s.product_name,
                "supplier_name":    s.supplier_name,
                "supplier_platform": s.supplier_platform,
                "carrier":          s.carrier,
                "status":           s.status,
                "status_display":   s.get_status_display(),
                "order_date":       s.order_date.isoformat(),
                "shipped_at":       s.shipped_at.isoformat() if s.shipped_at else None,
                "estimated_delivery": s.estimated_delivery.isoformat() if s.estimated_delivery else None,
                "delivered_at":     s.delivered_at.isoformat() if s.delivered_at else None,
                "admin_notes":      s.admin_notes,
            }
            for s in ships
        ]})

    def patch(self, request, shipment_id):
        """Update shipment status and notes from admin panel."""
        try:
            s = ShipmentTracking.objects.get(id=shipment_id)
        except ShipmentTracking.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        for field in ("status", "carrier", "carrier_tracking_url", "admin_notes",
                      "shipped_at", "estimated_delivery", "delivered_at"):
            if field in request.data:
                setattr(s, field, request.data[field])
        s.save()
        return Response({"updated": True, "tracking_id": s.tracking_id})


class AdminTokenPricingView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        pricing = TokenPricing.objects.all()
        return Response({"pricing": [
            {"id": p.id, "label": p.label, "tokens_per_pack": p.tokens_per_pack,
             "price_naira": str(p.price_naira), "is_active": p.is_active}
            for p in pricing
        ]})

    def post(self, request):
        p = TokenPricing.objects.create(
            label           = request.data.get("label", "Standard Pack"),
            tokens_per_pack = request.data.get("tokens_per_pack", 2),
            price_naira     = request.data.get("price_naira", 200),
            is_active       = request.data.get("is_active", True),
            updated_by      = request.user,
        )
        return Response({"id": p.id, "label": p.label, "created": True})

    def patch(self, request, pricing_id):
        try:
            p = TokenPricing.objects.get(id=pricing_id)
        except TokenPricing.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
        for field in ("label", "tokens_per_pack", "price_naira", "is_active"):
            if field in request.data:
                setattr(p, field, request.data[field])
        p.updated_by = request.user
        p.save()
        return Response({"updated": True})
