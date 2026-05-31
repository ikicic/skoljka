from django.urls import path

from skoljka.apps.problems import admin_views
from skoljka.apps.tags import views as tag_views

urlpatterns = [
    path("", admin_views.problem_admin_list, name="problem_admin_list"),
    path("tags/", tag_views.tag_admin_list, name="tag_admin_list"),
    path("tags/<int:pk>/edit/", tag_views.tag_admin_edit, name="tag_admin_edit"),
    path("tags/<int:pk>/delete/", tag_views.tag_admin_delete, name="tag_admin_delete"),
    path("new/", admin_views.problem_create, name="problem_create"),
    path("<int:pk>/edit/", admin_views.problem_edit, name="problem_edit"),
    path("<int:pk>/delete/", admin_views.problem_delete, name="problem_delete"),
]
