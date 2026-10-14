from django.conf import settings
from django.contrib.syndication.views import Feed
from django.urls import reverse

from .models import Post


class LatestPostsFeed(Feed):
    """RSS feed of the 20 most recent posts at /feed/."""

    def title(self):
        return settings.SITE_NAME

    def description(self):
        return settings.SITE_TAGLINE

    def link(self):
        return reverse("blog:list")

    def items(self):
        return Post.objects.published().prefetch_related("tags")[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt

    def item_pubdate(self, item):
        return item.published_at

    def item_updateddate(self, item):
        return item.updated_at

    def item_categories(self, item):
        return [tag.name for tag in item.tags.all()]
