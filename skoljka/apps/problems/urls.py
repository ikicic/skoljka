from django.urls import path

from skoljka.apps.problems import views

urlpatterns = [
    path("", views.problem_list, name="problem_list"),
    path("export/pdf/", views.problem_list_pdf, name="problem_list_pdf"),
    path("suggest-tags/", views.problem_suggest_tags, name="problem_suggest_tags"),
    path("<int:pk>/", views.problem_detail, name="problem_detail"),
]
