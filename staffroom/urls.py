from django.urls import path

from . import views

app_name = "staffroom"

urlpatterns = [
    path("", views.PostListView.as_view(), name="list"),
    path("new/", views.PostCreateView.as_view(), name="create"),
    path("<int:pk>/", views.PostDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.PostUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.PostDeleteView.as_view(), name="delete"),
    path("<int:pk>/download/", views.AttachmentDownloadView.as_view(), name="download"),
]
