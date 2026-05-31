from django.urls import path

from skoljka.apps.importer import views

urlpatterns = [
    path("pdf/", views.pdf_import, name="pdf_import"),
    path("pdf/transcribe/", views.pdf_transcribe, name="pdf_transcribe"),
    path("pdf/transcribe/active/", views.pdf_transcribe_active, name="pdf_transcribe_active"),
    path("pdf/transcribe/<uuid:job_id>/", views.pdf_transcribe_status, name="pdf_transcribe_status"),
    path("pdf/transcribe/<uuid:job_id>/cancel/", views.pdf_transcribe_cancel, name="pdf_transcribe_cancel"),
    path("pdf/transcribe/<uuid:job_id>/delete/", views.pdf_transcribe_delete, name="pdf_transcribe_delete"),
    path("pdf/suggest-tags/", views.pdf_suggest_tags, name="pdf_suggest_tags"),
    path("pdf/confirm/", views.pdf_confirm, name="pdf_confirm"),
]
