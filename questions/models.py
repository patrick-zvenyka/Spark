from datetime import timedelta

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .validators import validate_no_blocked_words, validate_no_personal_info


def generate_reference() -> str:
    """Historical migration compatibility. New questions no longer use references."""
    import secrets
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


class QuestionQuerySet(models.QuerySet):
    def public(self):
        """Answered questions published on the public board."""
        return self.filter(
            is_public=True,
            status__in=[Question.Status.ANSWERED, Question.Status.CLOSED],
            answered_at__isnull=False,
        )

    def unanswered(self):
        return self.filter(status=Question.Status.OPEN)

    def overdue(self):
        return self.filter(status=Question.Status.OPEN, due_at__lt=timezone.now())

    def for_user(self, user):
        """Questions a staff member is allowed to see in their inbox."""
        if not user.is_authenticated or not user.is_active:
            return self.none()
        if user.is_system_admin:
            return self.all()
        if user.department_id:
            return self.filter(department_id=user.department_id)
        return self.none()


class Question(models.Model):
    """A question asked by an authenticated student."""

    asked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="questions",
    )

    class Status(models.TextChoices):
        OPEN = "open", "Awaiting answer"
        ANSWERED = "answered", "Answered"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Removed"

    department = models.ForeignKey("core.Department", on_delete=models.PROTECT, related_name="questions")
    topic = models.ForeignKey(
        "core.Topic", null=True, blank=True, on_delete=models.SET_NULL, related_name="questions"
    )
    title = models.CharField(
        max_length=160,
        validators=[MinLengthValidator(8), validate_no_personal_info, validate_no_blocked_words],
    )
    body = models.TextField(
        max_length=4000,
        validators=[MinLengthValidator(15), validate_no_personal_info, validate_no_blocked_words],
    )

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    is_public = models.BooleanField(default=True, help_text="Show on the public board once answered.")

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    due_at = models.DateTimeField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    overdue_notified_at = models.DateTimeField(null=True, blank=True, editable=False)

    forwarded_from = models.ForeignKey(
        "core.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    moderation_note = models.TextField(
        blank=True, help_text="Reason for removal. Shown to the student on the tracking page."
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    view_count = models.PositiveIntegerField(default=0)

    objects = QuestionQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["department", "status"]),
            models.Index(fields=["status", "due_at"]),
            models.Index(fields=["is_public", "status", "answered_at"]),
        ]

    def __str__(self):
        return f"Question #{self.pk}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.due_at:
            self.due_at = self.created_at + timedelta(hours=self.department.response_time_hours)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("questions:detail", args=[self.pk])

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    @property
    def is_overdue(self):
        return self.status == self.Status.OPEN and self.due_at < timezone.now()

    @property
    def is_visible_publicly(self):
        return (
            self.is_public
            and self.answered_at is not None
            and self.status in (self.Status.ANSWERED, self.Status.CLOSED)
        )

    @property
    def can_receive_answers(self):
        return self.status in (self.Status.OPEN, self.Status.ANSWERED)

    @property
    def response_time(self):
        if self.answered_at:
            return self.answered_at - self.created_at
        return None

    @property
    def answered_on_time(self):
        return bool(self.answered_at and self.answered_at <= self.due_at)

    def mark_answered(self):
        if self.status == self.Status.OPEN:
            self.status = self.Status.ANSWERED
        if not self.answered_at:
            self.answered_at = timezone.now()
        self.save(update_fields=["status", "answered_at", "updated_at"])


class Answer(models.Model):
    """An answer is always signed by the lecturer who gave it (accountability)."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="answers")
    body = models.TextField(max_length=8000, validators=[MinLengthValidator(10)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Answer by {self.author} to Question #{self.question.pk}"

    @property
    def was_edited(self):
        return (self.updated_at - self.created_at).total_seconds() > 60

    def can_edit(self, user):
        return user.is_authenticated and (user.is_system_admin or user.pk == self.author_id)
