from django.urls import path
from .views import InitiatePaymentView, VerifyPaymentView, TrackCommissionView, TransactionHistoryView

urlpatterns = [
    path("initiate/",    InitiatePaymentView.as_view(),  name="initiate-payment"),
    path("verify/",      VerifyPaymentView.as_view(),    name="verify-payment"),
    path("commission/",  TrackCommissionView.as_view(),  name="track-commission"),
    path("history/",     TransactionHistoryView.as_view(), name="payment-history"),
]
