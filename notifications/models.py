from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        NEW_QUESTION = "new_question", "New question"
        FORWARDED = "forwarded", "Question forwarded"
        OVERDUE = "overdue", "Question overdue"
        STAFFROOM_POST = "staffroom_post", "Staff room post"
        STAFFROOM_COMMENT = "staffroom_comment", "Staff room comment"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.recipient}: {self.title}"
