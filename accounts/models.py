from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    """A staff account. Students never get accounts: they ask anonymously."""

    class Role(models.TextChoices):
        LECTURER = "lecturer", "Lecturer"
        HOD = "hod", "Head of department"
        ADMIN = "admin", "System administrator"

    class Employment(models.TextChoices):
        PERMANENT = "permanent", "Permanent"
        TEMPORARY = "temporary", "Temporary"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.LECTURER)
    employment_type = models.CharField(
        max_length=20, choices=Employment.choices, default=Employment.PERMANENT
    )
    department = models.ForeignKey(
        "core.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff",
    )
    title = models.CharField(max_length=30, blank=True, help_text="e.g. Dr, Mr, Ms, Prof")
    contract_end = models.DateField(
        null=True, blank=True, help_text="Optional end date for temporary lecturers."
    )

    class Meta:
        ordering = ["first_name", "last_name", "username"]

    def __str__(self):
        return self.display_name

    def clean(self):
        super().clean()
        needs_department = self.role in (self.Role.LECTURER, self.Role.HOD)
        if needs_department and not self.is_superuser and not self.department_id:
            raise ValidationError({"department": "Lecturers and heads of department must belong to a department."})

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    @property
    def display_name(self):
        name = self.get_full_name() or self.username
        return f"{self.title} {name}" if self.title else name

    @property
    def initials(self):
        parts = [p for p in (self.first_name, self.last_name) if p]
        if not parts:
            return self.username[:2].upper()
        return "".join(p[0] for p in parts).upper()

    @property
    def is_temporary(self):
        return self.employment_type == self.Employment.TEMPORARY

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    @property
    def is_system_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_hod(self):
        return self.role == self.Role.HOD

    @property
    def can_supervise(self):
        return self.is_hod or self.is_system_admin

    def can_answer_for(self, department):
        """Can this user see and answer questions for `department`?"""
        if not self.is_active:
            return False
        if self.is_system_admin:
            return True
        department_id = getattr(department, "pk", department)
        return bool(self.department_id) and self.department_id == department_id

    def can_manage_department(self, department):
        """Can this user see supervision statistics for `department`?"""
        if self.is_system_admin:
            return True
        department_id = getattr(department, "pk", department)
        return self.is_hod and self.department_id == department_id
