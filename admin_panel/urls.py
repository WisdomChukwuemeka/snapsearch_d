from django.urls import path
from .views import (
    AdminDashboardStatsView, AdminPaymentsView, AdminSearchHistoryView,
    AdminCommissionView, AdminShipmentView, AdminTokenPricingView,
)

urlpatterns = [
    path("stats/",               AdminDashboardStatsView.as_view(), name="admin-stats"),
    path("payments/",            AdminPaymentsView.as_view(),       name="admin-payments"),
    path("searches/",            AdminSearchHistoryView.as_view(),  name="admin-searches"),
    path("commissions/",         AdminCommissionView.as_view(),     name="admin-commissions"),
    path("shipments/",           AdminShipmentView.as_view(),       name="admin-shipments"),
    path("shipments/<int:shipment_id>/", AdminShipmentView.as_view(), name="admin-shipment-update"),
    path("pricing/",             AdminTokenPricingView.as_view(),   name="admin-pricing"),
    path("pricing/<int:pricing_id>/", AdminTokenPricingView.as_view(), name="admin-pricing-update"),
]
