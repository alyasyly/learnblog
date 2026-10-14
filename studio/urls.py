from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.StudioLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="studio:login"), name="logout"),
    path("posts/", views.post_list, name="posts"),
    path("posts/new/", views.post_edit, name="post_create"),
    path("posts/<int:pk>/", views.post_edit, name="post_edit"),
    path("posts/<int:pk>/delete/", views.post_delete, name="post_delete"),
    path("preview/", views.preview, name="preview"),
    path("comments/", views.comments, name="comments"),
    path("comments/<int:pk>/", views.comment_action, name="comment_action"),
    path("tags/", views.tags, name="tags"),
    path("tags/<int:pk>/delete/", views.tag_delete, name="tag_delete"),
]
