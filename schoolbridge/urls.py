from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("staffroom/", include("staffroom.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("notifications/", include("notifications.urls")),
    path("feedback/", include("feedback.urls")),
    path("", include("questions.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
