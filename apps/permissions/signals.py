from django.dispatch import Signal

# Sender is the object's model class.
objectpermissions_changed = Signal(providing_args=['instance', 'content_type'])
