import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Comment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("body", models.TextField(max_length=2000, verbose_name="متن")),
                (
                    "is_approved",
                    models.BooleanField(
                        default=True,
                        help_text="اگر برداشته شود، دیدگاه برای دیگران نمایش داده نمی‌شود.",
                        verbose_name="تأیید شده",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت"),
                ),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="blog_comments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="نویسنده",
                    ),
                ),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="blog.post",
                        verbose_name="نوشته",
                    ),
                ),
            ],
            options={
                "verbose_name": "دیدگاه",
                "verbose_name_plural": "دیدگاه‌ها",
                "ordering": ["created_at"],
            },
        ),
    ]
