from django.conf import settings
from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, resolve_url
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from .forms import CommentForm
from .models import Comment, Post, Tag
from .resume_data import RESUME, SECTION_KEYS


class PostListView(ListView):
    """Home page, tag pages (`/tag/<slug>/`) and search (`?q=`) in one view."""

    model = Post
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = settings.POSTS_PER_PAGE

    def get_queryset(self):
        queryset = Post.objects.published().prefetch_related("tags")

        self.tag = None
        slug = self.kwargs.get("slug")
        if slug:
            self.tag = get_object_or_404(Tag, slug=slug)
            queryset = queryset.filter(tags=self.tag)

        self.query = self.request.GET.get("q", "").strip()
        if self.query:
            queryset = queryset.filter(
                Q(title__icontains=self.query)
                | Q(summary__icontains=self.query)
                | Q(body__icontains=self.query)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tag"] = self.tag
        context["query"] = self.query
        context["all_tags"] = Tag.objects.with_post_counts()
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = "blog/post_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        queryset = Post.objects.prefetch_related("tags")
        # The site owner (staff) can preview drafts and scheduled posts.
        if not self.request.user.is_staff:
            queryset = queryset.published()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        live = Post.objects.published()

        # Comments: everyone sees approved ones; authors also see their own
        # pending ones; staff see everything.
        user = self.request.user
        comments = post.comments.select_related("author")
        if user.is_staff:
            pass
        elif user.is_authenticated:
            comments = comments.filter(Q(is_approved=True) | Q(author=user))
        else:
            comments = comments.filter(is_approved=True)
        context["comments"] = comments
        draft = self.request.session.pop(f"comment_draft_{post.pk}", "")
        context["comment_form"] = CommentForm(initial={"body": draft})

        context["newer"] = context["older"] = None
        if post.published_at:
            context["newer"] = (
                live.filter(published_at__gt=post.published_at)
                .order_by("published_at")
                .first()
            )
            context["older"] = (
                live.filter(published_at__lt=post.published_at)
                .order_by("-published_at")
                .first()
            )

        tag_ids = list(post.tags.values_list("id", flat=True))
        context["related"] = (
            live.filter(tags__in=tag_ids)
            .exclude(pk=post.pk)
            .annotate(shared=Count("tags"))
            .order_by("-shared", "-published_at")
            .prefetch_related("tags")[:3]
            if tag_ids
            else []
        )
        return context


class CommentCreateView(View):
    """POST /post/<slug>/comment/ — only for signed-in users."""

    http_method_names = ["post"]

    def post(self, request, slug):
        queryset = Post.objects.all() if request.user.is_staff else Post.objects.published()
        post = get_object_or_404(queryset, slug=slug)
        post_url = post.get_absolute_url()

        if not request.user.is_authenticated:
            return redirect_to_login(f"{post_url}#comment-form", resolve_url("accounts:login"))

        form = CommentForm(request.POST, user=request.user, post=post)
        if form.is_valid():
            approved = settings.COMMENTS_AUTO_APPROVE or request.user.is_staff
            comment = Comment.objects.create(
                post=post,
                author=request.user,
                body=form.cleaned_data["body"],
                is_approved=approved,
            )
            if approved:
                messages.success(request, "دیدگاهت ثبت شد.")
                return redirect(f"{post_url}#comment-{comment.pk}")
            messages.info(request, "دیدگاهت ثبت شد و بعد از تأیید نمایش داده می‌شود.")
            return redirect(f"{post_url}#comments")

        # Keep what was typed so nothing is lost, and say what went wrong.
        request.session[f"comment_draft_{post.pk}"] = request.POST.get("body", "")[
            : Comment.BODY_MAX_LENGTH * 2
        ]
        errors = [error for errs in form.errors.values() for error in errs]
        messages.error(request, errors[0] if errors else "دیدگاه ثبت نشد.")
        return redirect(f"{post_url}#comment-form")


class CommentDeleteView(View):
    """POST /comment/<pk>/delete/ — the comment's author or staff."""

    http_method_names = ["post"]

    def post(self, request, pk):
        comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk)
        post_url = comment.post.get_absolute_url()

        if not request.user.is_authenticated:
            return redirect_to_login(f"{post_url}#comments", resolve_url("accounts:login"))
        if comment.author_id != request.user.pk and not request.user.is_staff:
            raise PermissionDenied

        comment.delete()
        messages.success(request, "دیدگاه حذف شد.")
        return redirect(f"{post_url}#comments")


class ResumeView(TemplateView):
    """/resume/ — content comes from blog/resume_data.py."""

    template_name = "blog/resume.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["resume"] = RESUME
        context["resume_filled"] = any(RESUME.get(key) for key in SECTION_KEYS)
        return context
