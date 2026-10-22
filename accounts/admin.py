from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "display_name",
        "email",
        "role",
        "employment_type",
        "department",
        "is_active",
        "last_login",
    )
    list_filter = ("role", "employment_type", "department", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    list_select_related = ("department",)
    autocomplete_fields = ("department",)
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Schoolbridge",
            {"fields": ("title", "role", "department", "employment_type", "contract_end")},
        ),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "Schoolbridge",
            {"fields": ("first_name", "last_name", "email", "title", "role", "department", "employment_type")},
        ),
    )
    actions = ("deactivate_users", "activate_users")

    @admin.action(description="Deactivate selected accounts")
    def deactivate_users(self, request, queryset):
        updated = queryset.exclude(pk=request.user.pk).update(is_active=False)
        self.message_user(request, f"{updated} account(s) deactivated.")

    @admin.action(description="Activate selected accounts")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} account(s) activated.")
