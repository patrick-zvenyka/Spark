from django.contrib import admin

from .models import Answer, Question


class AnswerInline(admin.StackedInline):
    model = Answer
    extra = 0
    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "department", "topic", "status", "is_public", "created_at", "due_at", "answered_at")
    list_filter = ("status", "is_public", "department", "topic")
    search_fields = ("title", "body", "asked_by__username")
    date_hierarchy = "created_at"
    list_select_related = ("department", "topic")
    readonly_fields = (
        "created_at", "updated_at", "answered_at", "overdue_notified_at",
        "forwarded_from", "moderated_by", "view_count",
    )
    fields = (
        "asked_by", "department", "topic", "title", "body", "status", "is_public",
        "due_at", "moderation_note", "created_at", "updated_at", "answered_at",
        "overdue_notified_at", "forwarded_from", "moderated_by", "view_count",
    )
    inlines = [AnswerInline]
    actions = ("hide_from_board", "publish_on_board")

    def has_add_permission(self, request):
        # Students create questions through the authenticated site flow.
        return False

    @admin.action(description="Hide selected questions from the board")
    def hide_from_board(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_public=False)} question(s) hidden.")

    @admin.action(description="Publish selected questions on the board")
    def publish_on_board(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_public=True)} question(s) published.")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "author", "created_at")
    list_filter = ("question__department",)
    search_fields = ("body", "question__title", "author__username")
    list_select_related = ("question", "author")
    autocomplete_fields = ("author",)
    raw_id_fields = ("question",)
