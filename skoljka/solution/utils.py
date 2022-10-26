def can_mark_as_official(user, task):
    """Check if the user can mark his/her solution as official for the
    given task."""
    return user.id == task.author_id or \
            user.has_perm('solution.mark_as_official_solution')
