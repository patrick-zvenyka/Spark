from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class StaffRequiredMixin(LoginRequiredMixin):
    """Any signed-in staff member (all accounts are staff accounts)."""


class SupervisorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Heads of department and system administrators."""

    def test_func(self):
        return self.request.user.can_supervise


class SystemAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_system_admin
