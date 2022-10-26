from skoljka.settings.common import *
import skoljka.settings.common

def _check_mandatory_values(values):
    for value in values:
        if not hasattr(common, value):
            raise Exception(
                "Critical error! settings.{} missing, please check local.py "
                "and local.template.py".format(value))

_check_mandatory_values([
    'REGISTRATION_CONTACT_EMAIL',
])
