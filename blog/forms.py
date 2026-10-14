from django import forms
from django.conf import settings
from django.utils import timezone

from .models import Comment


class CommentForm(forms.Form):
    body = forms.CharField(
        label="دیدگاه",
        strip=True,
        min_length=2,
        max_length=Comment.BODY_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "dir": "auto",
                "maxlength": Comment.BODY_MAX_LENGTH,
                "placeholder": "دیدگاهت را بنویس…",
                "aria-label": "متن دیدگاه",
            }
        ),
        error_messages={
            "required": "متن دیدگاه را بنویس.",
            "min_length": "دیدگاه خیلی کوتاه است.",
            "max_length": f"دیدگاه نباید از {Comment.BODY_MAX_LENGTH} نویسه بیشتر باشد.",
        },
    )
    # Honeypot: invisible to people, tempting to bots.
    hp_company_fax = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    def __init__(self, *args, user=None, post=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.post = post

    def clean_hp_company_fax(self):
        if self.cleaned_data.get("hp_company_fax"):
            raise forms.ValidationError("درخواست نامعتبر است.")
        return ""

    def clean(self):
        cleaned = super().clean()
        user, body = self.user, cleaned.get("body")
        if not (user and user.is_authenticated and body):
            return cleaned

        # Slow down floods (the owner is exempt).
        if not user.is_staff:
            last = (
                Comment.objects.filter(author=user)
                .order_by("-created_at")
                .values_list("created_at", flat=True)
                .first()
            )
            if last and (timezone.now() - last).total_seconds() < settings.COMMENT_COOLDOWN_SECONDS:
                raise forms.ValidationError(
                    "کمی صبر کن؛ بین دو دیدگاه چند ثانیه فاصله لازم است."
                )

        # Refuse an exact repeat of the same comment on the same post.
        if self.post is not None and Comment.objects.filter(
            post=self.post, author=user, body=body
        ).exists():
            raise forms.ValidationError("همین دیدگاه را قبلاً فرستاده‌ای.")
        return cleaned
