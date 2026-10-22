from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = f"{settings.SB_SITE_NAME} administration"
admin.site.site_title = f"{settings.SB_SITE_NAME} admin"
admin.site.index_title = "Accounts, departments and moderation"

urlpatterns = [
    path(settings.SB_ADMIN_URL, admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("staffroom/", include("staffroom.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("notifications/", include("notifications.urls")),
    path("feedback/", include("feedback.urls")),
    path("", include("questions.urls")),
    path("", include("core.urls")),
]
