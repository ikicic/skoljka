VIEW = 1
EDIT = 2
DELETE = 3
EDIT_PERMISSIONS = 4
ADD_MEMBERS = 5  # For UserGroup.
# Reserved: 6

# Default permissions related to a model.
MODEL_DEFAULT = [VIEW, EDIT, DELETE, EDIT_PERMISSIONS]

# Ordered list of (constant value, name).
PERMISSIONS = [
    ('view', VIEW),
    ('edit', EDIT),
    ('delete', DELETE),
    ('edit_permissions', EDIT_PERMISSIONS),
    ('add_members', ADD_MEMBERS),
]

PERMISSION_NAMES = {value: key for key, value in PERMISSIONS}

# Dictionary constant name / 'shortcut' -> list of related constants
PERMISSION_GROUPS = {key: [value] for key, value in PERMISSIONS}
PERMISSION_GROUPS.update(
    {
        # 'shortcuts'...
        'default': MODEL_DEFAULT,
    }
)
