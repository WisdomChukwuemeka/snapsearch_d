from django.urls import path
from .views import TokenBalanceView

urlpatterns = [
    path("balance/", TokenBalanceView.as_view(), name="token-balance"),
]
