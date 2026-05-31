from django.core.checks import Error, register

from skoljka.apps.accounts.challenges import configured_challenges


@register()
def check_registration_math_challenges(app_configs, **kwargs):
    try:
        configured_challenges()
    except ValueError as exc:
        return [
            Error(
                str(exc),
                id="accounts.E001",
            )
        ]
    return []
