from django.contrib import admin

from .models import Comment, Post


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    autocomplete_fields = ("author",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "department", "author", "is_pinned", "created_at")
    list_filter = ("kind", "department", "is_pinned")
    search_fields = ("title", "body", "course")
    list_select_related = ("department", "author")
    autocomplete_fields = ("author",)
    inlines = [CommentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    search_fields = ("body",)
    autocomplete_fields = ("author",)
