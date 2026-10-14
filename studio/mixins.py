from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only active staff users may open the studio.

    Anonymous visitors are sent to the studio login page (settings.LOGIN_URL);
    logged-in users without staff status get a 403.
    """

    def test_func(self):
        user = self.request.user
        return user.is_active and user.is_staff
