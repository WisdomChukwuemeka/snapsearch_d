from django.urls import path
from .views import UserShipmentsView, TrackShipmentView

urlpatterns = [
    path("",                           UserShipmentsView.as_view(),  name="my-shipments"),
    path("<str:tracking_id>/",         TrackShipmentView.as_view(),  name="track-shipment"),
]
