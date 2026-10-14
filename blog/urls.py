from django.urls import path

from .feeds import LatestPostsFeed
from .views import (
    CommentCreateView,
    CommentDeleteView,
    PostDetailView,
    PostListView,
    ResumeView,
)

app_name = "blog"

urlpatterns = [
    path("", PostListView.as_view(), name="list"),
    path("tag/<str:slug>/", PostListView.as_view(), name="tag"),
    path("post/<str:slug>/", PostDetailView.as_view(), name="detail"),
    path("post/<str:slug>/comment/", CommentCreateView.as_view(), name="comment_add"),
    path("comment/<int:pk>/delete/", CommentDeleteView.as_view(), name="comment_delete"),
    path("resume/", ResumeView.as_view(), name="resume"),
    path("feed/", LatestPostsFeed(), name="feed"),
]
