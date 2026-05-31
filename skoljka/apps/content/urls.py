from django.urls import path

from skoljka.apps.content import views

urlpatterns = [
    path(
        "<int:content_id>/attachments/",
        views.attachment_upload,
        name="content_attachment_upload",
    ),
    path(
        "<int:content_id>/attachments/<str:name>/",
        views.attachment_delete,
        name="content_attachment_delete",
    ),
]
