from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

import skoljka.apps.accounts.urls
import skoljka.apps.content.urls
import skoljka.apps.problems.admin_urls
import skoljka.apps.problems.urls
import skoljka.apps.search.urls
import skoljka.apps.importer.urls
import skoljka.apps.sources.admin_urls
import skoljka.apps.sources.urls
import skoljka.apps.tags.urls
import skoljka.apps.tracking.urls
import skoljka.apps.lists.urls
import skoljka.apps.news.urls
from skoljka.apps.accounts import home_views
from skoljka.apps.content import help_views
from skoljka.config.views import versioned_javascript_catalog

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path(
        "jsi18n/<str:language>/<str:version>.js",
        versioned_javascript_catalog,
        name="javascript-catalog",
    ),
    path("accounts/", include(skoljka.apps.accounts.urls)),
    path("content/", include(skoljka.apps.content.urls)),
    path("help/", help_views.help_index, name="help_index"),
    path("help/format/", help_views.format_help, name="help_format"),
    path("archive/manage/", include(skoljka.apps.sources.admin_urls)),
    path("archive/", include(skoljka.apps.sources.urls)),
    path("problems/manage/", include(skoljka.apps.problems.admin_urls)),
    path("problems/import/", include(skoljka.apps.importer.urls)),
    path("problems/", include(skoljka.apps.problems.urls)),
    path("tags/", include(skoljka.apps.tags.urls)),
    path("search/", include(skoljka.apps.search.urls)),
    path("tracking/", include(skoljka.apps.tracking.urls)),
    path("lists/", include(skoljka.apps.lists.urls)),
    path("news/", include(skoljka.apps.news.urls)),
    path("", home_views.home, name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.ENABLE_DEBUG_TOOLBAR:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
