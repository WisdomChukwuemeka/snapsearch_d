from django.urls import path
from . import views

urlpatterns = [
    path("analyze/", views.AnalyzeImageView.as_view(), name="analyze-image"),
    path("ask/", views.AskProductView.as_view(), name="ask-product"),
    path("history/", views.SearchHistoryView.as_view(), name="search-history"),
]
