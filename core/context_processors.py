from django.conf import settings


def schoolbridge(request):
    data = {
        "SITE_NAME": settings.SB_SITE_NAME,
        "INSTITUTION_NAME": settings.SB_INSTITUTION_NAME,
        "DEFAULT_RESPONSE_HOURS": settings.SB_DEFAULT_RESPONSE_HOURS,
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from questions.models import Question

        data["unread_notifications"] = user.notifications.filter(is_read=False).count()
        data["inbox_open_count"] = Question.objects.for_user(user).filter(status=Question.Status.OPEN).count()
    return data
