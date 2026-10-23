from django.contrib import messages
from django.contrib.auth import login, logout, views as auth_views
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import CreateView

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .forms import ProfileForm, StudentSignupForm


class StudentSignupView(CreateView):
    form_class = StudentSignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("questions:board")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Your student account has been created.")
        return response


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.is_teacher or self.request.user.is_hod or self.request.user.is_system_admin:
            return reverse_lazy("dashboard:home")
        return reverse_lazy("questions:student_inbox")


class LogoutView(View):
    template_name = "accounts/logout.html"

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("core:home")
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "You have been logged out.")
        return redirect("core:home")


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)
