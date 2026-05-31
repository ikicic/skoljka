from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "skoljka.apps.accounts"
    label = "accounts"

    def ready(self) -> None:
        from skoljka.apps.accounts.challenges import configured_challenges

        configured_challenges()
        import skoljka.apps.accounts.checks  # noqa: F401
        import skoljka.apps.accounts.signals  # noqa: F401
