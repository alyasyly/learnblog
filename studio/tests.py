"""Tests for the writing studio (login, editor, preview, publishing, permissions)."""
import re

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from blog.models import Post, Tag

class StudioTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.staff = U.objects.create_user("ali", password="pw12345!x", is_staff=True)
        self.plain = U.objects.create_user("bob", password="pw12345!x")
        self.c = Client()

    def login(self):
        self.assertTrue(self.c.login(username="ali", password="pw12345!x"))

    def test_anonymous_redirected_to_login(self):
        for name in ["dashboard", "posts", "post_create", "tags"]:
            r = self.c.get(reverse(f"studio:{name}"))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn("/studio/login/", r["Location"])
        r = self.c.post(reverse("studio:preview"), {"body": "x"})
        self.assertEqual(r.status_code, 302)

    def test_non_staff_cannot_login(self):
        r = self.c.post(reverse("studio:login"), {"username": "bob", "password": "pw12345!x"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "اجازه")
        self.c.login(username="bob", password="pw12345!x")
        self.assertEqual(self.c.get(reverse("studio:dashboard")).status_code, 302)

    def test_login_flow(self):
        self.assertEqual(self.c.get(reverse("studio:login")).status_code, 200)
        r = self.c.post(reverse("studio:login"), {"username": "ali", "password": "bad"})
        self.assertContains(r, "درست نیست")
        r = self.c.post(reverse("studio:login"), {"username": "ali", "password": "pw12345!x"})
        self.assertRedirects(r, reverse("studio:dashboard"), fetch_redirect_response=False)

    def test_pages_render_empty_and_filled(self):
        self.login()
        for name in ["dashboard", "posts", "post_create", "tags"]:
            self.assertEqual(self.c.get(reverse(f"studio:{name}")).status_code, 200, name)
        self.c.post(reverse("studio:post_create"), {"title": "x", "body": "hello", "status": "draft", "action": "save"})
        for name in ["dashboard", "posts", "tags"]:
            self.assertEqual(self.c.get(reverse(f"studio:{name}")).status_code, 200, name)

    def test_create_publish_edit_delete(self):
        self.login()
        r = self.c.post(reverse("studio:post_create"), {
            "title": "یادگیری ریکشن", "body": "## سلام\n\nمتن **من**", "summary": "",
            "status": "draft", "published_at": "", "slug": "", "tags_text": "پایتون, جنگو،  پایتون , گیت",
            "action": "save"})
        p = Post.objects.get()
        self.assertRedirects(r, reverse("studio:post_edit", args=[p.pk]), fetch_redirect_response=False)
        self.assertEqual(p.state, "draft")
        self.assertTrue(p.slug)
        self.assertEqual({t.name for t in p.tags.all()}, {"پایتون", "جنگو", "گیت"}); self.assertEqual(p.tags.count(), 3)
        # draft invisible on public site, visible for staff
        anon = Client()
        self.assertEqual(anon.get(p.get_absolute_url()).status_code, 404)
        self.assertEqual(self.c.get(p.get_absolute_url()).status_code, 200)
        # publish button
        r = self.c.post(reverse("studio:post_edit", args=[p.pk]), {
            "title": p.title, "body": p.body, "summary": "", "status": "draft",
            "published_at": "", "slug": p.slug, "tags_text": "پایتون", "action": "publish"})
        p.refresh_from_db()
        self.assertEqual(p.state, "live")
        self.assertIsNotNone(p.published_at)
        self.assertEqual(p.tags.count(), 1)
        self.assertEqual(anon.get(p.get_absolute_url()).status_code, 200)
        # edit page prefilled
        r = self.c.get(reverse("studio:post_edit", args=[p.pk]))
        self.assertContains(r, 'value="پایتون"')
        self.assertContains(r, "یادگیری ریکشن")
        # scheduled date (datetime-local format)
        r = self.c.post(reverse("studio:post_edit", args=[p.pk]), {
            "title": p.title, "body": p.body, "summary": "", "status": "published",
            "published_at": "2099-01-01T10:30", "slug": p.slug, "tags_text": "", "action": "save"})
        p.refresh_from_db()
        self.assertEqual(p.state, "scheduled")
        self.assertEqual(anon.get(p.get_absolute_url()).status_code, 404)
        r = self.c.get(reverse("studio:post_edit", args=[p.pk]))
        self.assertContains(r, "2099-01-01T10:30")
        # list filters + search
        for q in ["?status=scheduled", "?status=draft", "?status=live", "?q=سلام", f"?tag={Tag.objects.first().slug}"]:
            self.assertEqual(self.c.get(reverse("studio:posts") + q).status_code, 200, q)
        # delete
        self.assertContains(self.c.get(reverse("studio:post_delete", args=[p.pk])), "حذف")
        r = self.c.post(reverse("studio:post_delete", args=[p.pk]))
        self.assertRedirects(r, reverse("studio:posts"), fetch_redirect_response=False)
        self.assertFalse(Post.objects.exists())

    def test_validation_errors(self):
        self.login()
        r = self.c.post(reverse("studio:post_create"), {"title": "", "body": "", "status": "draft", "action": "save"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "ذخیره نشد")
        self.assertFalse(Post.objects.exists())

    def test_duplicate_slug_error(self):
        self.login()
        Post.objects.create(title="a", body="b", slug="same")
        r = self.c.post(reverse("studio:post_create"), {"title": "t", "body": "b", "status": "draft", "slug": "same", "action": "save"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

    def test_preview_endpoint(self):
        self.login()
        r = self.c.post(reverse("studio:preview"), {"body": "## عنوان\n\n```python\nprint(1)\n```"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("codehilite", data["html"])
        self.assertEqual(self.c.get(reverse("studio:preview")).status_code, 405)

    def test_csrf_enforced_on_preview(self):
        self.login()
        strict = Client(enforce_csrf_checks=True)
        strict.login(username="ali", password="pw12345!x")
        self.assertEqual(strict.post(reverse("studio:preview"), {"body": "x"}).status_code, 403)

    def test_tags_page_and_delete(self):
        self.login()
        t = Tag.objects.create(name="موقت")
        self.assertContains(self.c.get(reverse("studio:tags")), "موقت")
        self.assertEqual(self.c.get(reverse("studio:tag_delete", args=[t.pk])).status_code, 405)
        self.c.post(reverse("studio:tag_delete", args=[t.pk]))
        self.assertFalse(Tag.objects.exists())

    def test_logout_is_post(self):
        self.login()
        r = self.c.post(reverse("studio:logout"))
        self.assertRedirects(r, reverse("studio:login"), fetch_redirect_response=False)

    def test_blog_links_to_studio_for_staff(self):
        self.login()
        r = self.c.get("/")
        self.assertContains(r, reverse("studio:dashboard"))


# ---------------------------------------------------------------- comments
from blog.models import PUBLISHED, Comment  # noqa: E402


class StudioCommentTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.staff = U.objects.create_user("ali", password="pw12345!x", is_staff=True)
        self.plain = U.objects.create_user("bob", password="pw12345!x")
        self.post = Post.objects.create(title="Hello", body="text", status=PUBLISHED)
        self.comment = Comment.objects.create(post=self.post, author=self.plain, body="nice one")
        self.c = Client()

    def act(self, action, **extra):
        data = {"action": action, **extra}
        return self.c.post(reverse("studio:comment_action", args=[self.comment.pk]), data)

    def test_comments_page_requires_staff(self):
        r = self.c.get(reverse("studio:comments"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/studio/login/", r["Location"])
        self.c.login(username="bob", password="pw12345!x")
        r = self.c.get(reverse("studio:comments"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/studio/login/", r["Location"])

    def test_staff_sees_comments(self):
        self.c.login(username="ali", password="pw12345!x")
        r = self.c.get(reverse("studio:comments"))
        self.assertContains(r, "nice one")
        self.assertContains(r, "bob")

    def test_hide_approve_and_delete(self):
        self.c.login(username="ali", password="pw12345!x")
        r = self.act("hide")
        self.assertRedirects(r, reverse("studio:comments"), fetch_redirect_response=False)
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_approved)

        self.act("approve")
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_approved)

        self.act("delete")
        self.assertFalse(Comment.objects.exists())

    def test_actions_need_post_and_staff(self):
        url = reverse("studio:comment_action", args=[self.comment.pk])
        self.c.login(username="bob", password="pw12345!x")
        self.c.post(url, {"action": "delete"})
        self.assertTrue(Comment.objects.exists())
        self.c.logout()
        self.c.login(username="ali", password="pw12345!x")
        self.assertEqual(self.c.get(url).status_code, 405)

    def test_redirect_target_must_be_local(self):
        self.c.login(username="ali", password="pw12345!x")
        r = self.act("hide", next="https://evil.example/")
        self.assertRedirects(r, reverse("studio:comments"), fetch_redirect_response=False)
