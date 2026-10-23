from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import TemplateView

from questions.models import Question


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = "tutors/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        queryset = Question.objects.for_user(user)
        now = timezone.now()

        context.update(
            department=user.department,
            stats=queryset.aggregate(
                total=Count("pk"),
                open=Count("pk", filter=Q(status=Question.Status.OPEN)),
                overdue=Count(
                    "pk",
                    filter=Q(status=Question.Status.OPEN, due_at__lt=now),
                ),
                answered=Count("pk", filter=Q(status=Question.Status.ANSWERED)),
                closed=Count("pk", filter=Q(status=Question.Status.CLOSED)),
            ),
            recent_questions=(
                queryset.select_related("department", "topic", "asked_by")
                .order_by("-created_at")[:8]
            ),
            overdue_questions=(
                queryset.filter(status=Question.Status.OPEN, due_at__lt=now)
                .select_related("department", "topic")
                .order_by("due_at")[:5]
            ),
        )
        return context
