from django.dispatch import Signal

object_tag_ids_changed_high_priority = Signal(
    providing_args=['old_tag_ids', 'new_tag_ids']
)
object_tag_ids_changed = Signal(providing_args=['old_tag_ids', 'new_tag_ids'])
