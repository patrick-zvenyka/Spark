from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 25

    def get_queryset(self):
        return self.request.user.notifications.all()


class NotificationOpenView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        if notification.url and url_has_allowed_host_and_scheme(
            notification.url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(notification.url)
        return redirect("notifications:list")


class MarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return redirect("notifications:list")
