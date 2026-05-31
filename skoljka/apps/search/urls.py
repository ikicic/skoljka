from django.urls import path

from skoljka.apps.search import views

urlpatterns = [
    path("", views.search_view, name="search"),
    path("pdf/", views.search_pdf, name="search_pdf"),
]
