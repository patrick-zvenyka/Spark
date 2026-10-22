from django.db.models import Count, Q
from django.views.generic import TemplateView

from dashboard.stats import question_stats
from questions.models import Question

from .models import Department


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stats"] = question_stats(Question.objects.all())
        ctx["departments"] = (
            Department.objects.filter(is_active=True)
            .annotate(
                answered_count=Count(
                    "questions",
                    filter=Q(questions__answered_at__isnull=False, questions__is_public=True),
                )
            )
            .order_by("name")
        )
        ctx["recent_answers"] = (
            Question.objects.public()
            .select_related("department", "topic")
            .prefetch_related("answers__author")
            .order_by("-answered_at")[:6]
        )
        return ctx


class GuideView(TemplateView):
    template_name = "core/guide.html"


class RulesView(TemplateView):
    template_name = "core/rules.html"
