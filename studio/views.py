from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from blog.jalali import format_jalali
from blog.markdown_utils import render_markdown
from blog.models import DRAFT, PUBLISHED, Comment, Post, Tag

from .forms import PostForm, StudioAuthForm

PAGE_SIZE = 12
ACTIVITY_WEEKS = 12

staff_required = user_passes_test(
    lambda u: u.is_active and u.is_staff, login_url="studio:login"
)


def _state_counts():
    now = timezone.now()
    return Post.objects.aggregate(
        total=Count("id"),
        live=Count("id", filter=Q(status=PUBLISHED, published_at__lte=now)),
        scheduled=Count("id", filter=Q(status=PUBLISHED, published_at__gt=now)),
        draft=Count("id", filter=Q(status=DRAFT)),
    )


def _greeting(now):
    hour = now.hour
    if hour < 5 or hour >= 21:
        return "شب بخیر"
    if hour < 12:
        return "صبح بخیر"
    if hour < 17:
        return "روز بخیر"
    return "عصر بخیر"


class StudioLoginView(LoginView):
    template_name = "studio/login.html"
    authentication_form = StudioAuthForm
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect("studio:dashboard")
        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------- dashboard
@staff_required
def dashboard(request):
    now = timezone.now()
    local_now = timezone.localtime(now)

    # Posts created per week for the last N weeks (oldest -> newest).
    buckets = [0] * ACTIVITY_WEEKS
    since = now - timedelta(weeks=ACTIVITY_WEEKS)
    for created in Post.objects.filter(created_at__gte=since).values_list(
        "created_at", flat=True
    ):
        index = (now - created).days // 7
        if 0 <= index < ACTIVITY_WEEKS:
            buckets[ACTIVITY_WEEKS - 1 - index] += 1
    peak = max(buckets) or 1
    activity = [
        {"count": count, "height": 6 + round(count / peak * 94) if count else 3}
        for count in buckets
    ]

    total_words = sum(len(body.split()) for body in Post.objects.values_list("body", flat=True))

    context = {
        "stats": _state_counts(),
        "total_words": total_words,
        "tag_total": Tag.objects.count(),
        "recent": Post.objects.prefetch_related("tags").order_by("-updated_at")[:6],
        "resume": Post.objects.filter(status=DRAFT).order_by("-updated_at").first(),
        "activity": activity,
        "activity_total": sum(buckets),
        "greeting": _greeting(local_now),
        "today": format_jalali(local_now.date()),
        "display_name": request.user.get_short_name() or request.user.get_username(),
    }
    return render(request, "studio/dashboard.html", context)


# --------------------------------------------------------------- post list
@staff_required
def post_list(request):
    now = timezone.now()
    posts = Post.objects.prefetch_related("tags")

    status = request.GET.get("status", "")
    if status == "live":
        posts = posts.filter(status=PUBLISHED, published_at__lte=now)
    elif status == "scheduled":
        posts = posts.filter(status=PUBLISHED, published_at__gt=now)
    elif status == "draft":
        posts = posts.filter(status=DRAFT)
    else:
        status = ""

    query = request.GET.get("q", "").strip()
    if query:
        posts = posts.filter(
            Q(title__icontains=query) | Q(summary__icontains=query) | Q(body__icontains=query)
        )

    tag_slug = request.GET.get("tag", "").strip()
    active_tag = None
    if tag_slug:
        active_tag = Tag.objects.filter(slug=tag_slug).first()
        if active_tag:
            posts = posts.filter(tags=active_tag)

    page_obj = Paginator(posts.distinct().order_by("-updated_at"), PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    context = {
        "page_obj": page_obj,
        "paginator": page_obj.paginator,
        "is_paginated": page_obj.has_other_pages(),
        "counts": _state_counts(),
        "status": status,
        "query": query,
        "active_tag": active_tag,
        "tags": Tag.objects.annotate(n=Count("posts")).order_by("name"),
    }
    return render(request, "studio/post_list.html", context)


# ------------------------------------------------------------- create/edit
@staff_required
def post_edit(request, pk=None):
    post = get_object_or_404(Post, pk=pk) if pk else None

    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            obj = form.save(commit=False)
            action = request.POST.get("action", "save")
            if action == "publish":
                obj.status = PUBLISHED
            elif action == "draft":
                obj.status = DRAFT
            obj.save()
            form.save_tags(obj)

            if action == "publish":
                messages.success(request, "نوشته منتشر شد.")
            else:
                messages.success(request, "تغییرات ذخیره شد.")
            return redirect("studio:post_edit", pk=obj.pk)
        messages.error(request, "نوشته ذخیره نشد. خطاهای مشخص‌شده را برطرف کن.")
    else:
        form = PostForm(instance=post)

    context = {
        "form": form,
        "post": post,
        "tag_suggestions": Tag.objects.values_list("name", flat=True),
    }
    return render(request, "studio/post_form.html", context)


@staff_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        title = post.title
        post.delete()
        messages.success(request, f"«{title}» حذف شد.")
        return redirect("studio:posts")
    return render(request, "studio/post_confirm_delete.html", {"post": post})


# ----------------------------------------------------------------- preview
@staff_required
@require_POST
def preview(request):
    body = request.POST.get("body", "")
    rendered = render_markdown(body)
    return JsonResponse({"html": rendered.html, "toc": rendered.toc})


# -------------------------------------------------------------------- tags
@staff_required
def tags(request):
    items = Tag.objects.annotate(n=Count("posts")).order_by("name")
    return render(request, "studio/tags.html", {"tags": items})


@staff_required
@require_POST
def tag_delete(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    name = tag.name
    tag.delete()
    messages.success(request, f"برچسب «{name}» حذف شد.")
    return redirect("studio:tags")


# ---------------------------------------------------------------- comments
@staff_required
def comments(request):
    items = Comment.objects.select_related("author", "post")

    status = request.GET.get("status", "")
    if status == "approved":
        items = items.filter(is_approved=True)
    elif status == "pending":
        items = items.filter(is_approved=False)
    else:
        status = ""

    query = request.GET.get("q", "").strip()
    if query:
        items = items.filter(
            Q(body__icontains=query)
            | Q(author__username__icontains=query)
            | Q(post__title__icontains=query)
        )

    page_obj = Paginator(items.order_by("-created_at"), PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    context = {
        "page_obj": page_obj,
        "paginator": page_obj.paginator,
        "is_paginated": page_obj.has_other_pages(),
        "counts": Comment.objects.aggregate(
            total=Count("id"),
            approved=Count("id", filter=Q(is_approved=True)),
            pending=Count("id", filter=Q(is_approved=False)),
        ),
        "status": status,
        "query": query,
    }
    return render(request, "studio/comments.html", context)


@staff_required
@require_POST
def comment_action(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    action = request.POST.get("action")
    if action == "approve":
        comment.is_approved = True
        comment.save(update_fields=["is_approved"])
        messages.success(request, "دیدگاه نمایش داده می‌شود.")
    elif action == "hide":
        comment.is_approved = False
        comment.save(update_fields=["is_approved"])
        messages.success(request, "دیدگاه پنهان شد.")
    elif action == "delete":
        comment.delete()
        messages.success(request, "دیدگاه حذف شد.")
    else:
        messages.error(request, "عمل نامعتبر است.")

    target = request.POST.get("next", "")
    if not (
        target
        and url_has_allowed_host_and_scheme(
            target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        )
    ):
        target = reverse("studio:comments")
    return redirect(target)
