from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.text import Truncator, slugify

from .markdown_utils import render_markdown

DRAFT = "draft"
PUBLISHED = "published"

WORDS_PER_MINUTE = 200

STATE_LABELS = {
    "draft": "پیش‌نویس",
    "scheduled": "زمان‌بندی‌شده",
    "live": "منتشر شده",
}


def unique_slug(model, source, pk=None, fallback="item"):
    """Build a unicode-friendly slug from `source` that is unique for `model`."""
    max_length = model._meta.get_field("slug").max_length
    # Keep the Persian half-space (ZWNJ) as a hyphen instead of gluing the words.
    base = slugify(source.replace("\u200c", "-"), allow_unicode=True)[:max_length].strip("-") or fallback
    slug = base
    counter = 2
    others = model.objects.all()
    if pk:
        others = others.exclude(pk=pk)
    while others.filter(slug=slug).exists():
        suffix = f"-{counter}"
        slug = base[: max_length - len(suffix)] + suffix
        counter += 1
    return slug


class TagQuerySet(models.QuerySet):
    def with_post_counts(self):
        """Tags that have at least one live post, annotated with `post_count`."""
        live = Q(posts__status=PUBLISHED, posts__published_at__lte=timezone.now())
        return self.annotate(post_count=Count("posts", filter=live)).filter(
            post_count__gt=0
        )


class Tag(models.Model):
    name = models.CharField("نام", max_length=50, unique=True)
    slug = models.SlugField(
        "اسلاگ", max_length=60, unique=True, allow_unicode=True, blank=True
    )

    objects = TagQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name = "برچسب"
        verbose_name_plural = "برچسب‌ها"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Tag, self.name, self.pk, fallback="tag")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:tag", kwargs={"slug": self.slug})


class PostQuerySet(models.QuerySet):
    def published(self):
        """Posts that are marked as published and whose date has arrived."""
        return self.filter(status=PUBLISHED, published_at__lte=timezone.now())


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = DRAFT, "پیش‌نویس"
        PUBLISHED = PUBLISHED, "منتشر شده"

    title = models.CharField("عنوان", max_length=200)
    slug = models.SlugField(
        "اسلاگ", max_length=220, unique=True, allow_unicode=True, blank=True
    )
    summary = models.TextField(
        "خلاصه",
        max_length=300,
        blank=True,
        help_text="یکی دو جمله برای نمایش روی کارت نوشته. اگر خالی بماند از متن ساخته می‌شود.",
    )
    body = models.TextField("متن (Markdown)")
    tags = models.ManyToManyField(
        Tag, verbose_name="برچسب‌ها", blank=True, related_name="posts"
    )
    status = models.CharField(
        "وضعیت", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    published_at = models.DateTimeField(
        "زمان انتشار",
        null=True,
        blank=True,
        help_text="اگر خالی بماند هنگام انتشار روی «الان» تنظیم می‌شود. زمان آینده = انتشار زمان‌بندی‌شده.",
    )
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "نوشته"
        verbose_name_plural = "نوشته‌ها"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Post, self.title, self.pk, fallback="post")
        if self.status == PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"slug": self.slug})

    @property
    def is_live(self):
        return (
            self.status == PUBLISHED
            and self.published_at is not None
            and self.published_at <= timezone.now()
        )

    @property
    def state(self):
        """'draft', 'scheduled' (published in the future) or 'live'."""
        if self.status != PUBLISHED:
            return "draft"
        if self.published_at and self.published_at > timezone.now():
            return "scheduled"
        return "live"

    @property
    def state_label(self):
        return STATE_LABELS[self.state]

    @cached_property
    def rendered(self):
        return render_markdown(self.body)

    @property
    def reading_time(self):
        """Estimated reading time in minutes (at least 1)."""
        words = len(self.body.split())
        return max(1, round(words / WORDS_PER_MINUTE))

    @property
    def excerpt(self):
        if self.summary:
            return self.summary
        return Truncator(strip_tags(self.rendered.html)).words(30)


class CommentQuerySet(models.QuerySet):
    def approved(self):
        return self.filter(is_approved=True)


class Comment(models.Model):
    """A reader's comment. Plain text only; shown escaped, never as HTML."""

    BODY_MAX_LENGTH = 2000

    post = models.ForeignKey(
        Post,
        verbose_name="نوشته",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="نویسنده",
        on_delete=models.CASCADE,
        related_name="blog_comments",
    )
    body = models.TextField("متن", max_length=BODY_MAX_LENGTH)
    is_approved = models.BooleanField(
        "تأیید شده",
        default=True,
        help_text="اگر برداشته شود، دیدگاه برای دیگران نمایش داده نمی\u200cشود.",
    )
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)

    objects = CommentQuerySet.as_manager()

    class Meta:
        ordering = ["created_at"]
        verbose_name = "دیدگاه"
        verbose_name_plural = "دیدگاه\u200cها"

    def __str__(self):
        return f"{self.author} · {Truncator(self.body).chars(40)}"
