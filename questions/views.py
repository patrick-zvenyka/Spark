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
from core.ratelimit import ask_limiter, track_limiter

from . import services
from .forms import AnswerForm, AskForm, ModerationForm, TrackForm
from .models import Answer, Question, normalize_code

SESSION_NEW_QUESTION = "sb_new_question"


# ----------------------------------------------------------------------
# Public (students)
# ----------------------------------------------------------------------
class AskView(FormView):
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
        question, raw_key = services.submit_question(
            department=data["department"], topic=data.get("topic"), title=data["title"], body=data["body"]
        )
        ask_limiter.hit(self.request)
        # Shown exactly once on the next page, then removed from the session.
        self.request.session[SESSION_NEW_QUESTION] = {"reference": question.reference, "key": raw_key}
        return redirect("questions:ask_done")


@method_decorator(never_cache, name="dispatch")
class AskDoneView(View):
    def get(self, request):
        data = request.session.pop(SESSION_NEW_QUESTION, None)
        if not data:
            return redirect("questions:track")
        question = get_object_or_404(Question.objects.select_related("department"), reference=data["reference"])
        return render(request, "questions/ask_done.html", {"question": question, "access_key": data["key"]})


class BoardView(ListView):
    template_name = "questions/board.html"
    context_object_name = "questions"
    paginate_by = 12

    def get_queryset(self):
        qs = (
            Question.objects.public()
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


class QuestionDetailView(View):
    def get(self, request, reference):
        question = get_object_or_404(
            Question.objects.select_related("department", "topic"), reference=normalize_code(reference)
        )
        if not question.is_visible_publicly:
            user = request.user
            if user.is_authenticated and user.can_answer_for(question.department):
                return redirect("questions:inbox_detail", reference=question.reference)
            raise Http404("Question not found")

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


@method_decorator(never_cache, name="dispatch")
class TrackView(FormView):
    template_name = "questions/track.html"
    form_class = TrackForm

    def post(self, request, *args, **kwargs):
        if track_limiter.exceeded(request):
            return self.render_to_response(
                self.get_context_data(form=TrackForm(), rate_limited=True), status=429
            )
        track_limiter.hit(request)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        question = form.cleaned_data["question"]
        return render(
            self.request,
            "questions/track_result.html",
            {"question": question, "answers": question.answers.select_related("author")},
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
                Q(title__icontains=self.query) | Q(body__icontains=self.query) | Q(reference__iexact=self.query)
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

    def get_question(self, reference):
        question = get_object_or_404(
            Question.objects.select_related("department", "topic", "forwarded_from", "moderated_by"),
            reference=normalize_code(reference),
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

    def get(self, request, reference):
        return self.render_page(self.get_question(reference))

    def post(self, request, reference):
        question = self.get_question(reference)
        form_name = request.POST.get("form")

        if form_name == "answer":
            if not question.can_receive_answers:
                messages.error(request, "This question is closed and cannot receive new answers.")
                return redirect("questions:inbox_detail", reference=question.reference)
            form = AnswerForm(request.POST)
            if form.is_valid():
                services.post_answer(question=question, author=request.user, body=form.cleaned_data["body"])
                if question.is_public:
                    messages.success(request, "Your answer is now on the public board.")
                else:
                    messages.success(request, "Answer saved. The question is hidden from the board, so only the student can see it.")
                return redirect("questions:inbox_detail", reference=question.reference)
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
                return redirect("questions:inbox_detail", reference=question.reference)
            return self.render_page(question, moderation_form=form, status=400)

        messages.error(request, "Unknown action.")
        return redirect("questions:inbox_detail", reference=question.reference)


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
        return reverse("questions:inbox_detail", args=[self.object.question.reference])
