# ide li ovo ovdje ili u __init__.py?

VIEW = 1
EDIT = 2
DELETE = 3
EDIT_PERMISSIONS = 4
ADD_MEMBERS = 5     # for Group
VIEW_SOLUTIONS = 6  # for Task (solution_settings)

# Default permissions related to a model.
MODEL_DEFAULT = [VIEW, EDIT, DELETE, EDIT_PERMISSIONS]

# Ordered list of (constant value, name)
# Any way to DRY this?
PERMISSIONS = [
    ('view', VIEW),
    ('edit', EDIT),
    ('delete', DELETE),
    ('edit_permissions', EDIT_PERMISSIONS),
    ('add_members', ADD_MEMBERS),
    ('view_solutions', VIEW_SOLUTIONS),
]

PERMISSION_NAMES = {value: key for key, value in PERMISSIONS}

# Dictionary constant name / 'shortcut' -> list of related constants
PERMISSION_GROUPS = {key: [value] for key, value in PERMISSIONS}
PERMISSION_GROUPS.update({
    # 'shortcuts'...
    'default': MODEL_DEFAULT
})
