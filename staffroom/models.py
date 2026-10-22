import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse


def validate_attachment(file):
    ext = os.path.splitext(file.name)[1].lower().lstrip(".")
    allowed = [e.lower() for e in settings.SB_ALLOWED_UPLOAD_EXTENSIONS]
    if ext not in allowed:
        raise ValidationError(f"Files of type .{ext} are not allowed. Allowed: {', '.join(allowed)}.")
    max_bytes = settings.SB_MAX_UPLOAD_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f"File is too large. The maximum size is {settings.SB_MAX_UPLOAD_MB} MB.")


class PostQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()
        if user.is_system_admin:
            return self.all()
        return self.filter(Q(department__isnull=True) | Q(department_id=user.department_id))


class Post(models.Model):
    """A shared staff-room post: handovers, resources and advice."""

    class Kind(models.TextChoices):
        HANDOVER = "handover", "Handover note"
        RESOURCE = "resource", "Resource"
        ADVICE = "advice", "Advice"
        NOTICE = "notice", "Notice"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="staffroom_posts")
    department = models.ForeignKey(
        "core.Department",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="staffroom_posts",
        help_text="Leave empty to share with the whole institution.",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.ADVICE)
    title = models.CharField(max_length=160)
    course = models.CharField(max_length=80, blank=True, help_text="Course or module code, if relevant.")
    body = models.TextField(max_length=10000)
    link = models.URLField(blank=True, help_text="Optional link to an external resource.")
    attachment = models.FileField(
        upload_to="staffroom/%Y/%m/", blank=True, validators=[validate_attachment]
    )
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("staffroom:detail", args=[self.pk])

    @property
    def attachment_name(self):
        return os.path.basename(self.attachment.name) if self.attachment else ""

    def can_edit(self, user):
        return user.is_authenticated and (user.is_system_admin or user.pk == self.author_id)

    def can_delete(self, user):
        if self.can_edit(user):
            return True
        return user.is_authenticated and user.is_hod and self.department_id == user.department_id


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="staffroom_comments")
    body = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"
