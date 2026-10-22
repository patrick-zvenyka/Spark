from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, ListView, UpdateView

from core.models import Department
from core.ratelimit import ask_limiter

from . import services
from .forms import AnswerForm, AskForm, ModerationForm
from .models import Answer, Question

# ----------------------------------------------------------------------
# Public (students)
# ----------------------------------------------------------------------
class AskView(LoginRequiredMixin, FormView):
    template_name = "questions/ask.html"
    form_class = AskForm

    def get_initial(self):
        initial = super().get_initial()
        slug = self.request.GET.get("department")
        if slug:
            department = Department.objects.filter(slug=slug, is_active=True).first()
            if department:
                initial["department"] = department
        return initial

    def post(self, request, *args, **kwargs):
        if ask_limiter.exceeded(request):
            messages.error(
                request,
                "You have asked several questions in a short time. Please wait a while before asking again.",
            )
            return redirect("questions:ask")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        data = form.cleaned_data
        question = services.submit_question(
            department=data["department"],
            topic=data.get("topic"),
            title=data["title"],
            body=data["body"],
            student=self.request.user,
        )
        ask_limiter.hit(self.request)
        return redirect("questions:student_inbox_detail", pk=question.pk)


class BoardView(LoginRequiredMixin, ListView):
    template_name = "questions/board.html"
    context_object_name = "questions"
    paginate_by = 12

    def get_queryset(self):
        qs = (
            Question.objects.exclude(status=Question.Status.REJECTED)
            .select_related("department", "topic")
            .prefetch_related("answers__author")
        )
        self.department = self.topic = None
        self.query = self.request.GET.get("q", "").strip()[:100]
        self.sort = self.request.GET.get("sort", "recent")

        department_slug = self.request.GET.get("department")
        if department_slug:
            self.department = Department.objects.filter(slug=department_slug).first()
            if self.department:
                qs = qs.filter(department=self.department)
                topic_slug = self.request.GET.get("topic")
                if topic_slug:
                    self.topic = self.department.topics.filter(slug=topic_slug).first()
                    if self.topic:
                        qs = qs.filter(topic=self.topic)

        if self.query:
            qs = qs.filter(
                Q(title__icontains=self.query) | Q(body__icontains=self.query) | Q(answers__body__icontains=self.query)
            ).distinct()

        if self.sort == "popular":
            return qs.order_by("-view_count", "-answered_at")
        return qs.order_by("-answered_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            departments=Department.objects.filter(is_active=True),
            current_department=self.department,
            current_topic=self.topic,
            topics=self.department.topics.filter(is_active=True) if self.department else [],
            query=self.query,
            sort=self.sort,
        )
        return ctx


class QuestionDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        question = get_object_or_404(
            Question.objects.select_related("department", "topic"), pk=pk
        )
        user = request.user
        if not question.is_visible_publicly and not user.is_authenticated:
            raise Http404("Question not found")
        if user.is_authenticated and user.can_answer_for(question.department) and not user.is_student:
            return redirect("questions:inbox_detail", pk=question.pk)

        if not request.user.is_authenticated:
            Question.objects.filter(pk=question.pk).update(view_count=F("view_count") + 1)

        related = (
            Question.objects.public()
            .filter(department=question.department)
            .exclude(pk=question.pk)
            .order_by("-answered_at")[:4]
        )
        return render(
            request,
            "questions/detail.html",
            {
                "question": question,
                "answers": question.answers.select_related("author"),
                "related": related,
            },
        )


# ----------------------------------------------------------------------
# Student inbox
# ----------------------------------------------------------------------
class StudentInboxView(LoginRequiredMixin, ListView):
    template_name = "questions/student_inbox.html"
    context_object_name = "questions"
    paginate_by = 20

    def get_queryset(self):
        return (
            Question.objects.filter(asked_by=self.request.user)
            .select_related("department", "topic")
            .prefetch_related("answers__author")
            .order_by("-created_at")
        )


class StudentInboxDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        question = get_object_or_404(
            Question.objects.select_related("department", "topic", "asked_by"),
            pk=pk,
            asked_by=request.user,
        )
        return render(
            request,
            "questions/student_inbox_detail.html",
            {
                "question": question,
                "answers": question.answers.select_related("author"),
            },
        )


# ----------------------------------------------------------------------
# Staff (department inbox)
# ----------------------------------------------------------------------
class InboxView(LoginRequiredMixin, ListView):
    template_name = "questions/inbox.html"
    context_object_name = "questions"
    paginate_by = 20
    STATUSES = ("open", "overdue", "answered", "closed", "rejected", "all")

    def get_base_queryset(self):
        user = self.request.user
        qs = Question.objects.for_user(user)
        self.department = None
        if user.is_system_admin:
            slug = self.request.GET.get("department")
            if slug:
                self.department = Department.objects.filter(slug=slug).first()
                if self.department:
                    qs = qs.filter(department=self.department)
        else:
            self.department = user.department
        return qs

    def get_queryset(self):
        now = timezone.now()
        base = self.get_base_queryset()
        S = Question.Status
        self.counts = base.aggregate(
            open=Count("pk", filter=Q(status=S.OPEN)),
            overdue=Count("pk", filter=Q(status=S.OPEN, due_at__lt=now)),
            answered=Count("pk", filter=Q(status=S.ANSWERED)),
            closed=Count("pk", filter=Q(status=S.CLOSED)),
            rejected=Count("pk", filter=Q(status=S.REJECTED)),
            all=Count("pk"),
        )

        self.status = self.request.GET.get("status", "open")
        if self.status not in self.STATUSES:
            self.status = "open"
        qs = base.select_related("department", "topic").annotate(num_answers=Count("answers"))
        if self.status == "overdue":
            qs = qs.filter(status=S.OPEN, due_at__lt=now)
        elif self.status != "all":
            qs = qs.filter(status=self.status)

        self.topic_id = self.request.GET.get("topic", "")
        if self.topic_id.isdigit():
            qs = qs.filter(topic_id=int(self.topic_id))

        self.query = self.request.GET.get("q", "").strip()[:100]
        if self.query:
            qs = qs.filter(
                Q(title__icontains=self.query) | Q(body__icontains=self.query)
            )

        if self.status in ("open", "overdue"):
            return qs.order_by("due_at")
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        tabs = [
            ("open", "Awaiting answer"),
            ("overdue", "Overdue"),
            ("answered", "Answered"),
            ("closed", "Closed"),
            ("rejected", "Removed"),
            ("all", "All"),
        ]
        ctx.update(
            tabs=[(key, label, self.counts[key]) for key, label in tabs],
            status=self.status,
            query=self.query,
            topic_id=self.topic_id,
            current_department=self.department,
            topics=self.department.topics.filter(is_active=True) if self.department else [],
            departments=Department.objects.all() if user.is_system_admin else [],
            no_department=not user.is_system_admin and not user.department_id,
        )
        return ctx


class InboxDetailView(LoginRequiredMixin, View):
    template_name = "questions/inbox_detail.html"

    def get_question(self, pk):
        question = get_object_or_404(
            Question.objects.select_related("department", "topic", "forwarded_from", "moderated_by"),
            pk=pk,
        )
        if not self.request.user.can_answer_for(question.department):
            raise PermissionDenied
        return question

    def render_page(self, question, answer_form=None, moderation_form=None, status=200):
        user = self.request.user
        return render(
            self.request,
            self.template_name,
            {
                "question": question,
                "answers": question.answers.select_related("author"),
                "answer_form": answer_form or AnswerForm(),
                "moderation_form": moderation_form or ModerationForm(question=question, user=user),
            },
            status=status,
        )

    def get(self, request, pk):
        return self.render_page(self.get_question(pk))

    def post(self, request, pk):
        question = self.get_question(pk)
        form_name = request.POST.get("form")

        if form_name == "answer":
            if not question.can_receive_answers:
                messages.error(request, "This question is closed and cannot receive new answers.")
                return redirect("questions:inbox_detail", pk=question.pk)
            form = AnswerForm(request.POST)
            if form.is_valid():
                services.post_answer(question=question, author=request.user, body=form.cleaned_data["body"])
                if question.is_public:
                    messages.success(request, "Your answer is now on the public board.")
                else:
                    messages.success(request, "Answer saved. The question is hidden from the board, so only the student can see it.")
                return redirect("questions:inbox_detail", pk=question.pk)
            return self.render_page(question, answer_form=form, status=400)

        if form_name == "moderate":
            form = ModerationForm(request.POST, question=question, user=request.user)
            if form.is_valid():
                data = form.cleaned_data
                services.moderate(
                    question=question,
                    actor=request.user,
                    action=data["action"],
                    department=data.get("department"),
                    note=data.get("note", ""),
                )
                messages.success(request, f"Done: {ModerationForm.ACTION_LABELS[data['action']].lower()}.")
                if not request.user.can_answer_for(question.department):
                    return redirect("questions:inbox")
                return redirect("questions:inbox_detail", pk=question.pk)
            return self.render_page(question, moderation_form=form, status=400)

        messages.error(request, "Unknown action.")
        return redirect("questions:inbox_detail", pk=question.pk)


class AnswerEditView(LoginRequiredMixin, UpdateView):
    model = Answer
    form_class = AnswerForm
    template_name = "questions/answer_form.html"

    def get_queryset(self):
        qs = Answer.objects.select_related("question", "question__department")
        if self.request.user.is_system_admin:
            return qs
        return qs.filter(author=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Answer updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("questions:inbox_detail", args=[self.object.question.pk])
