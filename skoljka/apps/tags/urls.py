from django.urls import path

from skoljka.apps.tags import views

urlpatterns = [
    path("api/", views.tag_api, name="tag_api"),
]
