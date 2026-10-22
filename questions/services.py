"""Business logic for questions, kept out of views so it is easy to test."""
from datetime import timedelta

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from notifications.models import Notification
from notifications.services import notify

from .models import Answer, Question


def department_staff(department, exclude=None):
    qs = User.objects.filter(department=department, is_active=True)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    return qs


@transaction.atomic
def submit_question(*, department, title, body, topic=None):
    """Create an anonymous question. Returns (question, formatted_private_key)."""
    question = Question(department=department, topic=topic, title=title, body=body)
    raw_key = question.set_access_key()
    question.save()
    notify(
        department_staff(department),
        kind=Notification.Kind.NEW_QUESTION,
        title=f"New question for {department.code}: {title[:90]}",
        message=f"Please answer within {department.response_time_hours} hours.",
        url=reverse("questions:inbox_detail", args=[question.reference]),
    )
    return question, raw_key


@transaction.atomic
def post_answer(*, question, author, body):
    if not question.can_receive_answers:
        raise ValueError("This question is not accepting answers.")
    answer = Answer.objects.create(question=question, author=author, body=body)
    question.mark_answered()
    return answer


@transaction.atomic
def forward_question(*, question, to_department, actor, note=""):
    from_department = question.department
    question.forwarded_from = from_department
    question.department = to_department
    question.topic = None
    # Keep the original clock running so delays stay visible.
    question.due_at = question.created_at + timedelta(hours=to_department.response_time_hours)
    question.moderated_by = actor
    question.save()
    message = f"Forwarded by {from_department.code}."
    if note:
        message += f" Note: {note}"
    notify(
        department_staff(to_department),
        kind=Notification.Kind.FORWARDED,
        title=f"Question forwarded to {to_department.code}: {question.title[:90]}",
        message=message,
        url=reverse("questions:inbox_detail", args=[question.reference]),
    )
    return question


def moderate(*, question, actor, action, department=None, note=""):
    S = Question.Status
    note = (note or "").strip()
    if action == "forward":
        return forward_question(question=question, to_department=department, actor=actor, note=note)
    if action == "publish":
        question.is_public = True
    elif action == "unpublish":
        question.is_public = False
    elif action == "close":
        question.status = S.CLOSED
    elif action == "reopen":
        question.status = S.ANSWERED if question.answered_at else S.OPEN
        question.moderation_note = ""
    elif action == "reject":
        question.status = S.REJECTED
        question.is_public = False
        question.moderation_note = note
    else:
        raise ValueError(f"Unknown moderation action: {action}")
    question.moderated_by = actor
    question.save()
    return question


def notify_overdue(now=None):
    """Alert department staff and heads about questions past their due time.

    Each question triggers at most one alert. Returns the number of questions processed.
    """
    now = now or timezone.now()
    overdue = (
        Question.objects.filter(status=Question.Status.OPEN, due_at__lt=now, overdue_notified_at__isnull=True)
        .select_related("department")
    )
    count = 0
    for question in overdue:
        notify(
            department_staff(question.department),
            kind=Notification.Kind.OVERDUE,
            title=f"Overdue: {question.title[:100]}",
            message=(
                f"This question has waited longer than the agreed "
                f"{question.department.response_time_hours} hours."
            ),
            url=reverse("questions:inbox_detail", args=[question.reference]),
        )
        Question.objects.filter(pk=question.pk).update(overdue_notified_at=now)
        count += 1
    return count
