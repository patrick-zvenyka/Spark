from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.StudentSignupView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("password/", views.PasswordChangeView.as_view(), name="password_change"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
