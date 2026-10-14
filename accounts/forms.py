from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()

# Names nobody but the site owner should appear as.
RESERVED_USERNAMES = {
    "admin",
    "administrator",
    "root",
    "staff",
    "moderator",
    "support",
    "system",
    "ادمین",
    "مدیر",
    "پشتیبان",
}


class SignupForm(UserCreationForm):
    """Sign-up with just a username and a password (no e-mail is collected)."""

    # Honeypot: hidden from people with CSS, but bots tend to fill every field.
    hp_company_fax = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    class Meta:
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "نام کاربری"
        self.fields["password1"].label = "گذرواژه"
        self.fields["password2"].label = "تکرار گذرواژه"
        self.fields["password2"].help_text = ""
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "autofocus": True}
        )
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"

    def clean_username(self):
        # The parent also rejects names that differ only in letter case.
        username = super().clean_username()
        if username and username.casefold() in RESERVED_USERNAMES:
            raise forms.ValidationError("این نام کاربری در دسترس نیست.")
        return username

    def clean_hp_company_fax(self):
        if self.cleaned_data.get("hp_company_fax"):
            raise forms.ValidationError("درخواست نامعتبر است.")
        return ""


class SiteAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "نام کاربری"
        self.fields["password"].label = "گذرواژه"
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "autofocus": True}
        )
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"
