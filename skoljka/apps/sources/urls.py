from django.urls import path

from skoljka.apps.sources import views

urlpatterns = [
    path("", views.source_list, name="source_list"),
    path("documents/<int:pk>/delete/", views.source_document_delete, name="source_document_delete"),
    path("<slug:slug>/pdf/", views.source_pdf, name="source_pdf"),
    path("<slug:slug>/delete-problems/", views.source_bulk_delete, name="source_bulk_delete"),
    path("<slug:slug>/<int:year>/bulk-edit/", views.source_year_bulk_edit, name="source_year_bulk_edit"),
    path("<slug:slug>/<int:year>/bulk-edit/save/", views.source_year_bulk_edit_save, name="source_year_bulk_edit_save"),
    path("<slug:slug>/<int:year>/pdf/", views.source_year_pdf, name="source_year_pdf"),
    path("<slug:slug>/<int:year>/delete-problems/", views.source_year_bulk_delete, name="source_year_bulk_delete"),
    path("<slug:slug>/<int:year>/", views.source_detail, name="source_year_detail"),
    path("<slug:slug>/", views.source_detail, name="source_detail"),
]
