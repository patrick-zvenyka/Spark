from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=12, unique=True, help_text="Short code, e.g. CS or ACC.")
    slug = models.SlugField(max_length=40, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Only active departments receive questions. Use this to pilot "
            "Schoolbridge in one or two departments before scaling."
        ),
    )
    response_time_hours = models.PositiveIntegerField(
        default=settings.SB_DEFAULT_RESPONSE_HOURS,
        validators=[MinValueValidator(1), MaxValueValidator(24 * 30)],
        help_text="Agreed period within which questions must be answered.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        if not self.slug:
            self.slug = slugify(self.code or self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('questions:board')}?department={self.slug}"

    @property
    def heads(self):
        from accounts.models import User

        return self.staff.filter(role=User.Role.HOD, is_active=True)


class Topic(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["department__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["department", "slug"], name="unique_topic_slug_per_department"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:90]
        super().save(*args, **kwargs)
