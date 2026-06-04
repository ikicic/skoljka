from django.urls import path

from skoljka.apps.sources import admin_views

urlpatterns = [
    path("", admin_views.source_admin_list, name="source_admin_list"),
    path("export/", admin_views.source_export, name="source_export"),
    path("documents/source-urls/", admin_views.source_document_source_urls, name="source_document_source_urls"),
    path("new/", admin_views.source_create, name="source_create"),
    path("new-inline/", admin_views.source_create_inline, name="source_create_inline"),
    path("<int:pk>/edit/", admin_views.source_edit, name="source_edit"),
]
