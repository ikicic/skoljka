from django.urls import path

from skoljka.apps.tracking import views

urlpatterns = [
    path("sources/<int:pk>/favorite/", views.toggle_favorite_source, name="toggle_favorite_source"),
    path("lists/<int:pk>/favorite/", views.toggle_favorite_problem_list, name="toggle_favorite_problem_list"),
    path("<int:pk>/solve/", views.toggle_solved, name="toggle_solved"),
    path("<int:pk>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
    path("<int:pk>/like/", views.toggle_like, name="toggle_like"),
    path("<int:pk>/note/", views.save_note, name="save_note"),
]
