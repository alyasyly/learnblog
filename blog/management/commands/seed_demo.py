from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import PUBLISHED, Post, Tag

DEMO_POSTS = [
    {
        "title": "اولین قدم‌ها با جنگو",
        "summary": "جنگو چطور کار می‌کند؟ مدل، ویو و قالب در چند دقیقه.",
        "tags": ["جنگو", "پایتون"],
        "days_ago": 6,
        "body": """## جنگو چیست؟

جنگو یک فریم‌ورک وب پایتونی است که بیشتر کارهای تکراری را خودش انجام می‌دهد.
سه بخش اصلی آن این‌هاست:

- **مدل (Model)**: ساختار داده‌ها و جدول‌های دیتابیس
- **ویو (View)**: منطق پاسخ به درخواست
- **قالب (Template)**: ظاهر صفحه

## ساخت اولین مدل

```python
from django.db import models


class Note(models.Model):
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```

بعد از تعریف مدل، این دو دستور را اجرا کن:

```bash
python manage.py makemigrations
python manage.py migrate
```

> هر وقت مدل را تغییر دادی، دوباره `makemigrations` و `migrate` را اجرا کن.

### نکته

ادمین جنگو بدون هیچ کدی آماده است؛ فقط مدل را در `admin.py` ثبت کن.
""",
    },
    {
        "title": "لیست و دیکشنری در پایتون: کی از کدام استفاده کنیم؟",
        "summary": "مقایسه‌ی سریع دو ساختار داده‌ی پرکاربرد پایتون.",
        "tags": ["پایتون", "ساختار داده"],
        "days_ago": 3,
        "body": """## تفاوت اصلی

لیست مجموعه‌ای **مرتب** از مقادیر است و دیکشنری مجموعه‌ای از جفت‌های **کلید و مقدار**.

| ویژگی | list | dict |
|---|---|---|
| دسترسی با | اندیس | کلید |
| ترتیب | حفظ می‌شود | به ترتیب درج |
| جستجوی عضو | O(n) | O(1) |

## مثال

```python
languages = ["python", "go", "rust"]
ages = {"python": 35, "go": 16, "rust": 11}

print(languages[0])      # python
print(ages["go"])        # 16
```

اگر مدام دنبال یک مقدار می‌گردی، دیکشنری معمولاً انتخاب بهتری است.
""",
    },
    {
        "title": "چند دستور Git که هر روز استفاده می‌کنم",
        "summary": "چک‌لیست کوتاه برای کار روزمره با Git.",
        "tags": ["گیت"],
        "days_ago": 1,
        "body": """## کارهای روزانه

```bash
git status            # وضعیت فعلی
git add -p            # انتخاب تکه‌تکه‌ی تغییرات
git commit -m "پیام"  # ثبت تغییرات
git switch -c feature # ساخت و رفتن به شاخه‌ی جدید
git log --oneline     # تاریخچه‌ی کوتاه
```

## برگرداندن اشتباه

اگر هنوز push نکرده‌ای و فقط پیام کامیت را می‌خواهی عوض کنی:

```bash
git commit --amend
```

**نکته:** روی شاخه‌ای که دیگران استفاده می‌کنند هیچ‌وقت تاریخچه را بازنویسی نکن.
""",
    },
]


class Command(BaseCommand):
    help = "Create a few demo posts so the site isn't empty (safe to run more than once)."

    def handle(self, *args, **options):
        now = timezone.now()
        created = 0
        for item in DEMO_POSTS:
            if Post.objects.filter(title=item["title"]).exists():
                continue
            post = Post.objects.create(
                title=item["title"],
                summary=item["summary"],
                body=item["body"],
                status=PUBLISHED,
                published_at=now - timedelta(days=item["days_ago"]),
            )
            for name in item["tags"]:
                tag, _ = Tag.objects.get_or_create(name=name)
                post.tags.add(tag)
            created += 1
        self.stdout.write(self.style.SUCCESS(f"{created} demo post(s) created."))
