from django.contrib import admin
from django.urls import path, include

# Custom admin site branding
admin.site.site_header  = "SnapSearch Admin"
admin.site.site_title   = "SnapSearch Admin"
admin.site.index_title  = "SnapSearch Control Panel"

urlpatterns = [
    path("admin/",          admin.site.urls),
    path("api/search/",     include("snapsearch.urls")),
    path("api/tokens/",     include("tokens.urls")),
    path("api/payments/",   include("payments.urls")),
    path("api/tracking/",   include("tracking.urls")),
    path("api/admin-panel/", include("admin_panel.urls")),
    path("api/geminisearch/", include("geminiSearch.urls")),
]
