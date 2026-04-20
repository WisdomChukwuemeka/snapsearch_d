from django.urls import path
from . import views

urlpatterns = [
    path("me/", views.MeView.as_view(), name="me"),
    path("balance/", views.TokenBalanceView.as_view(), name="token-balance"),
    path("initiate-payment/", views.InitiatePaymentView.as_view(), name="initiate-payment"),
    path("verify-payment/", views.VerifyPaymentView.as_view(), name="verify-payment"),
    path("transactions/", views.TransactionHistoryView.as_view(), name="transactions"),
]
