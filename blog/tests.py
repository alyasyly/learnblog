"""Tests for reader comments."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import PUBLISHED, Comment, Post

User = get_user_model()
PASSWORD = "Zx9!kLm2Qw"


@override_settings(COMMENT_COOLDOWN_SECONDS=0, COMMENTS_AUTO_APPROVE=True)
class CommentTests(TestCase):
    def setUp(self):
        self.post = Post.objects.create(title="Hello", body="some text", status=PUBLISHED)
        self.draft = Post.objects.create(title="Secret", body="not yet")  # a draft
        self.reader = User.objects.create_user("reader", password=PASSWORD)
        self.other = User.objects.create_user("other", password=PASSWORD)
        self.owner = User.objects.create_user("owner", password=PASSWORD, is_staff=True)
        self.add_url = reverse("blog:comment_add", args=[self.post.slug])

    def login(self, name="reader"):
        self.assertTrue(self.client.login(username=name, password=PASSWORD))

    # --- who can comment -------------------------------------------------
    def test_anonymous_is_sent_to_login(self):
        r = self.client.post(self.add_url, {"body": "hi there"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])
        self.assertIn("next=", r["Location"])
        self.assertEqual(Comment.objects.count(), 0)

    def test_signed_in_user_can_comment_and_it_is_shown(self):
        self.login()
        r = self.client.post(self.add_url, {"body": "سلام، ممنون از نوشته"})
        comment = Comment.objects.get()
        self.assertEqual((comment.author, comment.post), (self.reader, self.post))
        self.assertRedirects(
            r,
            f"{self.post.get_absolute_url()}#comment-{comment.pk}",
            fetch_redirect_response=False,
        )
        self.client.logout()  # even a visitor sees approved comments
        page = self.client.get(self.post.get_absolute_url())
        self.assertContains(page, "سلام، ممنون از نوشته")
        self.assertContains(page, "reader")

    def test_comment_form_is_shown_only_when_signed_in(self):
        page = self.client.get(self.post.get_absolute_url())
        self.assertNotContains(page, self.add_url)
        self.assertContains(page, reverse("accounts:signup"))
        self.login()
        page = self.client.get(self.post.get_absolute_url())
        self.assertContains(page, self.add_url)

    def test_get_is_not_allowed(self):
        self.login()
        self.assertEqual(self.client.get(self.add_url).status_code, 405)

    def test_cannot_comment_on_a_draft_unless_staff(self):
        url = reverse("blog:comment_add", args=[self.draft.slug])
        self.login()
        self.assertEqual(self.client.post(url, {"body": "peeking"}).status_code, 404)
        self.client.logout()
        self.login("owner")
        self.assertEqual(self.client.post(url, {"body": "note to self"}).status_code, 302)
        self.assertEqual(Comment.objects.filter(post=self.draft).count(), 1)

    # --- safety ------------------------------------------------------------
    def test_html_in_comments_is_escaped(self):
        self.login()
        self.client.post(self.add_url, {"body": "<script>alert(1)</script> hello"})
        page = self.client.get(self.post.get_absolute_url())
        self.assertContains(page, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(page, "<script>alert(1)</script>")

    def test_honeypot_blocks_bots(self):
        self.login()
        self.client.post(self.add_url, {"body": "buy things", "hp_company_fax": "x"})
        self.assertEqual(Comment.objects.count(), 0)

    def test_too_short_and_too_long_are_rejected(self):
        self.login()
        self.client.post(self.add_url, {"body": "a"})
        self.client.post(self.add_url, {"body": "x" * (Comment.BODY_MAX_LENGTH + 1)})
        self.assertEqual(Comment.objects.count(), 0)

    def test_exact_repeat_is_rejected(self):
        self.login()
        self.client.post(self.add_url, {"body": "same words"})
        self.client.post(self.add_url, {"body": "same words"})
        self.assertEqual(Comment.objects.count(), 1)
        self.client.post(self.add_url, {"body": "different words"})
        self.assertEqual(Comment.objects.count(), 2)

    @override_settings(COMMENT_COOLDOWN_SECONDS=60)
    def test_cooldown_slows_down_floods_but_not_the_owner(self):
        self.login()
        self.client.post(self.add_url, {"body": "first comment"})
        self.client.post(self.add_url, {"body": "second comment"})
        self.assertEqual(Comment.objects.filter(author=self.reader).count(), 1)

        self.client.logout()
        self.login("owner")
        self.client.post(self.add_url, {"body": "owner one"})
        self.client.post(self.add_url, {"body": "owner two"})
        self.assertEqual(Comment.objects.filter(author=self.owner).count(), 2)

    # --- moderation setting -------------------------------------------------
    @override_settings(COMMENTS_AUTO_APPROVE=False)
    def test_comments_wait_for_approval_when_enabled(self):
        self.login()
        self.client.post(self.add_url, {"body": "waiting for approval"})
        self.assertFalse(Comment.objects.get().is_approved)

        mine = self.client.get(self.post.get_absolute_url())
        self.assertContains(mine, "waiting for approval")
        self.assertContains(mine, "در انتظار تأیید")

        self.client.logout()
        self.assertNotContains(self.client.get(self.post.get_absolute_url()), "waiting for approval")
        self.login("other")
        self.assertNotContains(self.client.get(self.post.get_absolute_url()), "waiting for approval")

        self.client.logout()
        self.login("owner")
        self.assertContains(self.client.get(self.post.get_absolute_url()), "waiting for approval")

    @override_settings(COMMENTS_AUTO_APPROVE=False)
    def test_owner_comments_are_always_approved(self):
        self.login("owner")
        self.client.post(self.add_url, {"body": "from the owner"})
        self.assertTrue(Comment.objects.get().is_approved)

    # --- deleting -----------------------------------------------------------
    def make_comment(self, author=None):
        return Comment.objects.create(post=self.post, author=author or self.reader, body="to delete")

    def test_author_can_delete_own_comment(self):
        comment = self.make_comment()
        self.login()
        r = self.client.post(reverse("blog:comment_delete", args=[comment.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Comment.objects.exists())

    def test_other_users_cannot_delete(self):
        comment = self.make_comment()
        self.login("other")
        r = self.client.post(reverse("blog:comment_delete", args=[comment.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Comment.objects.exists())

    def test_staff_can_delete_any_comment(self):
        comment = self.make_comment()
        self.login("owner")
        self.client.post(reverse("blog:comment_delete", args=[comment.pk]))
        self.assertFalse(Comment.objects.exists())

    def test_anonymous_cannot_delete(self):
        comment = self.make_comment()
        r = self.client.post(reverse("blog:comment_delete", args=[comment.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])
        self.assertTrue(Comment.objects.exists())

    def test_deleting_a_post_removes_its_comments(self):
        self.make_comment()
        self.post.delete()
        self.assertFalse(Comment.objects.exists())


class ResumeAndGithubTests(TestCase):
    def test_resume_page_loads_and_is_linked_from_home(self):
        self.assertEqual(self.client.get(reverse("blog:resume")).status_code, 200)
        self.assertContains(self.client.get(reverse("blog:list")), 'href="/resume/"')

    def test_empty_resume_shows_a_friendly_note(self):
        r = self.client.get(reverse("blog:resume"))
        self.assertContains(r, "به‌زودی")

    def test_filled_resume_is_rendered(self):
        from unittest.mock import patch

        data = {
            "name": "Ali Test",
            "headline": "Python developer",
            "summary": "I build small things.",
            "experience": [
                {"title": "Developer", "company": "ACME", "period": "2024", "bullets": ["Shipped a blog"]}
            ],
            "skills": [{"group": "Backend", "skills": ["Python", "Django"]}],
        }
        with patch("blog.views.RESUME", data):
            r = self.client.get(reverse("blog:resume"))
        for text in ("Ali Test", "Python developer", "ACME", "Shipped a blog", "Django"):
            self.assertContains(r, text)
        self.assertNotContains(r, "به‌زودی")

    @override_settings(GITHUB_URL="https://github.com/example")
    def test_github_icon_is_shown_when_url_is_set(self):
        r = self.client.get(reverse("blog:list"))
        self.assertContains(r, 'href="https://github.com/example"')
        self.assertContains(r, 'aria-label="GitHub"')

    @override_settings(GITHUB_URL="")
    def test_github_icon_is_hidden_without_url(self):
        self.assertNotContains(self.client.get(reverse("blog:list")), 'aria-label="GitHub"')
