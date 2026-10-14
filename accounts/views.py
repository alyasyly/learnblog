from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import redirect, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView

from .forms import SignupForm, SiteAuthenticationForm

SIGNUP_WINDOW_SECONDS = 3600


def safe_next(request, fallback="blog:list"):
    """The `next` parameter if it points at this site, otherwise the home page."""
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return resolve_url(fallback)


def _signup_key(request):
    # Behind a reverse proxy REMOTE_ADDR is the proxy's address; see README.
    return f"signup:{request.META.get('REMOTE_ADDR', 'unknown')}"


class SignupView(FormView):
    template_name = "accounts/signup.html"
    form_class = SignupForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(safe_next(request))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.request.POST.get("next") or self.request.GET.get("next", "")
        return context

    def form_valid(self, form):
        key = _signup_key(self.request)
        if cache.get(key, 0) >= settings.SIGNUPS_PER_IP_PER_HOUR:
            form.add_error(
                None, "از این شبکه تعداد زیادی حساب ساخته شده؛ کمی بعد دوباره امتحان کن."
            )
            return self.form_invalid(form)

        user = form.save()
        cache.add(key, 0, SIGNUP_WINDOW_SECONDS)
        try:
            cache.incr(key)
        except ValueError:  # the key expired between add() and incr()
            cache.set(key, 1, SIGNUP_WINDOW_SECONDS)

        login(self.request, user)
        messages.success(self.request, f"خوش آمدی {user.get_username()}! حسابت ساخته شد.")
        return redirect(safe_next(self.request))


class SiteLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = SiteAuthenticationForm
    redirect_authenticated_user = True
    next_page = "blog:list"  # where to go when there is no ?next=
