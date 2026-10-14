"""Tests for public sign-up, login and logout."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()
PASSWORD = "Zx9!kLm2Qw"


def signup_data(username="sara", **extra):
    data = {"username": username, "password1": PASSWORD, "password2": PASSWORD}
    data.update(extra)
    return data


class SignupTests(TestCase):
    def setUp(self):
        cache.clear()  # the per-IP limit lives in the cache

    def test_signup_page_loads(self):
        self.assertEqual(self.client.get(reverse("accounts:signup")).status_code, 200)

    def test_signup_creates_a_plain_user_and_logs_in(self):
        r = self.client.post(reverse("accounts:signup"), signup_data())
        self.assertRedirects(r, reverse("blog:list"), fetch_redirect_response=False)
        user = User.objects.get(username="sara")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_signup_follows_a_safe_next_only(self):
        r = self.client.post(reverse("accounts:signup"), signup_data(next="/post/hello/"))
        self.assertRedirects(r, "/post/hello/", fetch_redirect_response=False)

        self.client.logout()
        r = self.client.post(
            reverse("accounts:signup"), signup_data("omid", next="https://evil.example/")
        )
        self.assertRedirects(r, reverse("blog:list"), fetch_redirect_response=False)

    def test_reserved_username_is_rejected(self):
        r = self.client.post(reverse("accounts:signup"), signup_data("Admin"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username__iexact="admin").exists())

    def test_username_is_unique_ignoring_case(self):
        User.objects.create_user("Sara", password=PASSWORD)
        r = self.client.post(reverse("accounts:signup"), signup_data("sara"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_mismatched_passwords_are_rejected(self):
        data = signup_data()
        data["password2"] = "something-else-1!"
        r = self.client.post(reverse("accounts:signup"), data)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_honeypot_blocks_bots(self):
        r = self.client.post(reverse("accounts:signup"), signup_data(hp_company_fax="spam"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.exists())

    @override_settings(SIGNUPS_PER_IP_PER_HOUR=1)
    def test_signups_per_ip_are_limited(self):
        self.client.post(reverse("accounts:signup"), signup_data("first"))
        self.client.logout()
        r = self.client.post(reverse("accounts:signup"), signup_data("second"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(User.objects.filter(username="first").exists())
        self.assertFalse(User.objects.filter(username="second").exists())

    def test_logged_in_user_is_sent_away_from_signup(self):
        User.objects.create_user("sara", password=PASSWORD)
        self.client.login(username="sara", password=PASSWORD)
        r = self.client.get(reverse("accounts:signup"))
        self.assertRedirects(r, reverse("blog:list"), fetch_redirect_response=False)

    def test_new_accounts_cannot_use_the_studio(self):
        self.client.post(reverse("accounts:signup"), signup_data())
        r = self.client.get(reverse("studio:dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/studio/login/", r["Location"])


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("sara", password=PASSWORD)

    def test_login_page_loads(self):
        self.assertEqual(self.client.get(reverse("accounts:login")).status_code, 200)

    def test_login_then_logout(self):
        r = self.client.post(
            reverse("accounts:login"), {"username": "sara", "password": PASSWORD}
        )
        self.assertRedirects(r, reverse("blog:list"), fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)

        r = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(r, reverse("blog:list"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_wrong_password_is_rejected(self):
        r = self.client.post(
            reverse("accounts:login"), {"username": "sara", "password": "wrong"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_follows_next(self):
        r = self.client.post(
            reverse("accounts:login"),
            {"username": "sara", "password": PASSWORD, "next": "/post/hello/"},
        )
        self.assertRedirects(r, "/post/hello/", fetch_redirect_response=False)

    def test_logout_requires_post(self):
        self.client.login(username="sara", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
