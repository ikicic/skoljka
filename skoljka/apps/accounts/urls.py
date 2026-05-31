from django.urls import path

from skoljka.apps.accounts import auth_views, profile_views, registration_views, simple_views

urlpatterns = [
    path("login/", auth_views.login_view, name="login"),
    path("password-reset/", auth_views.password_reset_request_view, name="password_reset"),
    path("password-reset/sent/", auth_views.password_reset_sent_view, name="password_reset_sent"),
    path(
        "password-reset/<str:uidb64>/<str:token>/",
        auth_views.password_reset_confirm_view,
        name="password_reset_confirm",
    ),
    path("password-reset/done/", auth_views.password_reset_done_view, name="password_reset_done"),
    path("register/", registration_views.register_view, name="register"),
    path("register/sent/", registration_views.register_sent_view, name="register_sent"),
    path("register/continue/<str:token>/", registration_views.register_confirm_view, name="register_confirm"),
    path(
        "register/challenge/<str:challenge_id>.png",
        registration_views.registration_challenge_image,
        name="registration_challenge_image",
    ),
    path(
        "register/label/<str:label_id>.png",
        registration_views.registration_label_image,
        name="registration_label_image",
    ),
    path("logout/", auth_views.logout_view, name="logout"),
    path("settings/", profile_views.settings_view, name="settings"),
    path("profile/<str:username>/liked/pdf/", profile_views.profile_liked_pdf, name="profile_liked_pdf"),
    path(
        "profile/<str:username>/bookmarked/pdf/",
        profile_views.profile_bookmarked_pdf,
        name="profile_bookmarked_pdf",
    ),
    path("profile/<str:username>/", profile_views.profile_view, name="profile"),
    path("about/", simple_views.about_view, name="about"),
    path("privacy/", simple_views.privacy_view, name="privacy"),
    path("terms/", simple_views.terms_view, name="terms"),
]
