from django.contrib import admin

from .models import Department, Topic


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 1
    fields = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "response_time_hours", "staff_count")
    list_editable = ("is_active", "response_time_hours")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    prepopulated_fields = {"slug": ("code",)}
    inlines = [TopicInline]

    @admin.display(description="Staff")
    def staff_count(self, obj):
        return obj.staff.filter(is_active=True).count()


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
