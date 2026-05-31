from django.urls import path

from skoljka.apps.news import views


urlpatterns = [
    path("", views.news_list, name="news_list"),
    path("manage/", views.news_manage, name="news_manage"),
    path("manage/new/", views.news_create, name="news_create"),
    path("manage/<int:pk>/edit/", views.news_edit, name="news_edit"),
    path("manage/<int:pk>/delete/", views.news_delete, name="news_delete"),
]
