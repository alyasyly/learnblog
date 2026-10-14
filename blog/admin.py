from django import forms
from django.contrib import admin, messages
from django.db.models import Count
from django.utils import timezone

from .models import DRAFT, PUBLISHED, Comment, Post, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "posts_total")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_posts_total=Count("posts"))

    @admin.display(description="تعداد نوشته", ordering="_posts_total")
    def posts_total(self, obj):
        return obj._posts_total


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "published_at", "updated_at")
    list_filter = ("status", "tags")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)
    date_hierarchy = "published_at"
    readonly_fields = ("created_at", "updated_at")
    actions = ["make_published", "make_draft"]
    save_on_top = True

    fieldsets = (
        (None, {"fields": ("title", "slug", "summary", "body")}),
        ("انتشار", {"fields": ("status", "published_at", "tags")}),
        ("اطلاعات", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "body":
            kwargs["widget"] = forms.Textarea(
                attrs={
                    "rows": 30,
                    "dir": "auto",
                    "style": "width: 100%; font-family: ui-monospace, Menlo, Consolas, monospace; line-height: 1.7;",
                }
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.action(description="انتشار نوشته‌های انتخاب‌شده")
    def make_published(self, request, queryset):
        now = timezone.now()
        count = 0
        for post in queryset:
            post.status = PUBLISHED
            if post.published_at is None:
                post.published_at = now
            post.save()
            count += 1
        self.message_user(request, f"{count} نوشته منتشر شد.", messages.SUCCESS)

    @admin.action(description="برگرداندن به پیش‌نویس")
    def make_draft(self, request, queryset):
        count = queryset.update(status=DRAFT)
        self.message_user(request, f"{count} نوشته به پیش‌نویس برگشت.", messages.SUCCESS)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("short_body", "author", "post", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    list_select_related = ("author", "post")
    search_fields = ("body", "author__username", "post__title")
    readonly_fields = ("created_at",)
    actions = ["approve", "hide"]

    @admin.display(description="متن")
    def short_body(self, obj):
        return obj.body[:60]

    @admin.action(description="تأیید و نمایش دیدگاه‌های انتخاب‌شده")
    def approve(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f"{count} دیدگاه نمایش داده می‌شود.", messages.SUCCESS)

    @admin.action(description="پنهان کردن دیدگاه‌های انتخاب‌شده")
    def hide(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f"{count} دیدگاه پنهان شد.", messages.SUCCESS)
