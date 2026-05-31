from django.apps import AppConfig


class TagsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "skoljka.apps.tags"
    label = "tags"

    def ready(self):
        from skoljka.apps.tags import signals  # noqa: F401
