from django.urls import path
from .views import (
    AnalyzeImageView,
    AskProductView,
    SearchHistoryView,
    ActiveProviderView,
)

urlpatterns = [
    path("analyze/",  AnalyzeImageView.as_view(),   name="geminisearch-analyze"),
    path("ask/",      AskProductView.as_view(),      name="geminisearch-ask"),
    path("history/",  SearchHistoryView.as_view(),   name="geminisearch-history"),
    path("provider/", ActiveProviderView.as_view(),  name="geminisearch-provider"),
]