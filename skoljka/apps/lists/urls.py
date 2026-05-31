from django.urls import path

from skoljka.apps.lists import editor_views, views

urlpatterns = [
    path("", views.list_index, name="list_index"),
    path("new/", views.list_create, name="list_create"),
    path("<int:pk>/pdf/", views.list_pdf, name="list_pdf"),
    path("<int:pk>/", views.list_detail, name="list_detail"),
    path("<int:pk>/bulk-edit/", views.list_bulk_edit, name="list_bulk_edit"),
    path("<int:pk>/bulk-edit/save/", views.list_bulk_edit_save, name="list_bulk_edit_save"),
    path("<int:pk>/edit/", editor_views.list_edit, name="list_edit"),
    path("<int:pk>/edit/details/", views.list_edit_details, name="list_edit_details"),
    path("<int:pk>/problem-search/", editor_views.list_problem_search, name="list_problem_search"),
    path("<int:pk>/items/save/", editor_views.list_items_save, name="list_items_save"),
]
