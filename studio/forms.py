import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from blog.models import Post, Tag

_TAG_SPLIT = re.compile(r"[,،\n]")


class StudioAuthForm(AuthenticationForm):
    """Login form that only lets staff members into the studio."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"placeholder": "نام کاربری", "dir": "ltr", "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"placeholder": "رمز عبور", "dir": "ltr"}
        )
        self.error_messages["invalid_login"] = "نام کاربری یا رمز عبور درست نیست."

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise ValidationError(
                "این حساب اجازه‌ی ورود به استودیو را ندارد.", code="not_staff"
            )


class PostForm(forms.ModelForm):
    # Comma-separated tag names; the editor's chip input keeps this in sync.
    tags_text = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Post
        fields = ["title", "slug", "summary", "body", "status", "published_at"]
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "عنوان نوشته", "autocomplete": "off", "dir": "auto"}
            ),
            "slug": forms.TextInput(
                attrs={"placeholder": "خودکار از روی عنوان", "dir": "ltr", "autocomplete": "off"}
            ),
            "summary": forms.Textarea(
                attrs={"rows": 3, "maxlength": 300, "placeholder": "یکی دو جمله برای کارت نوشته"}
            ),
            "body": forms.Textarea(
                attrs={
                    "dir": "auto",
                    "spellcheck": "false",
                    "placeholder": "از اینجا شروع کن. با Markdown می‌نویسی: ## برای عنوان، ``` برای کد.",
                }
            ),
            "status": forms.RadioSelect,
            "published_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["published_at"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]
        self.fields["body"].required = True
        if self.instance.pk:
            self.initial["tags_text"] = ", ".join(
                self.instance.tags.values_list("name", flat=True)
            )

    def tag_names(self):
        """Clean, de-duplicated tag names from the submitted text."""
        names, seen = [], set()
        for raw in _TAG_SPLIT.split(self.cleaned_data.get("tags_text", "")):
            name = " ".join(raw.split())[:50]
            if name and name.casefold() not in seen:
                seen.add(name.casefold())
                names.append(name)
        return names

    def save_tags(self, post):
        tags = []
        for name in self.tag_names():
            tag = Tag.objects.filter(name__iexact=name).first() or Tag.objects.create(
                name=name
            )
            tags.append(tag)
        post.tags.set(tags)
