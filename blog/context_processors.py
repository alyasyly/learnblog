from django.conf import settings


def site(request):
    """Make the site-wide texts available in every template."""
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "AUTHOR_NAME": settings.AUTHOR_NAME,
        "GITHUB_URL": settings.GITHUB_URL,
    }
