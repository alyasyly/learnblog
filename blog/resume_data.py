"""
محتوای صفحه‌ی رزومه (/resume/).

فقط مقدارهای زیر را پر کن و سایت را Reload کن؛ بخش‌های خالی در صفحه نمایش
داده نمی‌شوند. لازم نیست HTML بنویسی. لینک GitHub از تنظیم GITHUB_URL
خودکار در بخش تماس می‌آید.

نمونه‌ی هر بخش (جلوی # را بردار و با اطلاعات خودت عوض کن):

    "experience": [
        {
            "title": "توسعه‌دهنده‌ی بک‌اند",
            "company": "نام شرکت",
            "period": "۱۴۰۳ تا امروز",
            "description": "یک جمله درباره‌ی کارت.",
            "bullets": ["کاری که انجام دادی", "نتیجه‌ای که گرفتی"],
        },
    ],
    "skills": [
        {"group": "بک‌اند", "skills": ["Python", "Django", "SQL"]},
    ],
    "projects": [
        {"name": "وبلاگ من", "url": "https://github.com/...", "description": "توضیح کوتاه"},
    ],
    "education": [
        {"title": "کارشناسی مهندسی کامپیوتر", "school": "نام دانشگاه", "period": "۱۳۹۹ تا ۱۴۰۳"},
    ],
    "languages": [
        {"name": "انگلیسی", "level": "متوسط"},
    ],
    "contact": [
        {"label": "ایمیل", "url": "mailto:you@example.com"},
    ],
"""

RESUME = {
    "name": "",        # خالی بماند، نام نویسنده یا نام سایت نمایش داده می‌شود
    "headline": "",    # مثلاً: «توسعه‌دهنده‌ی وب | علاقه‌مند به پایتون»
    "location": "",    # مثلاً: «تهران»
    "summary": "",     # دو سه جمله درباره‌ی خودت
    "contact": [],
    "skills": [],
    "experience": [],
    "projects": [],
    "education": [],
    "languages": [],
}

# اگر یکی از این بخش‌ها پر باشد، صفحه «تکمیل‌شده» حساب می‌شود.
SECTION_KEYS = (
    "headline",
    "summary",
    "skills",
    "experience",
    "projects",
    "education",
    "languages",
)
