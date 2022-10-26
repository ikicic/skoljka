from collections import defaultdict

from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from skoljka.folder.models import Folder

register = template.Library()

def _descriptors_to_folders(descriptors):
    # Make sure tags are sorted (by their name).
    descriptors = [','.join(sorted(x.split(','))) for x in descriptors]

    # Force author_id=1.
    folders = Folder.objects.filter(cache_tags__in=descriptors, hidden=False,
        author_id=1)

    # Take only first N
    folders = list(folders[:len(descriptors)])

    # Put in the original order
    descriptor_position = {key: value for value, key in enumerate(descriptors)}
    return sorted(folders, key=lambda x: descriptor_position[x.cache_tags])

@register.simple_tag
def folder_url_by_id(folder_id):
    return '/folder/{}/'.format(folder_id)

@register.inclusion_tag('inc_folder_year_shortcuts.html', takes_context=True)
def folder_inline_year_shortcuts(context, folder_descriptors, split=1000):
    """
        Output links to folders and their (year-like) children in format:
            Parent folder with a long name          (main folder)
            '05 '06 '07 ... '12                     (year folders/children)

        folder_descriptors is a list of descriptions, one for each folder, where
        a description is a human readable info that uniquely describes the
        folder.
        When `split` parameter is given, result will be divided into
        `split`-sized results

        Currently, description is a string of comma-separated tags.
        For example: 'IMO' represent the main folder containing all IMO tasks.

        Optionally, the string can contain + sign, which is replaced with
        user's selected tag (from school class).
    """
    user = context.get('user')

    school_class = user and user.is_authenticated() \
        and user.get_profile().school_class

    chosen_tag = school_class and   \
        next((x[2] for x in settings.USERPROFILE_SCHOOL_CLASS_INFO \
            if x[0] == school_class), None)

    # Replace + with chosen tag (appropriate school class)
    if chosen_tag:
        folder_descriptors = [x.replace('+', chosen_tag) for x in folder_descriptors]

    # Find all main folders
    main_folders = _descriptors_to_folders(folder_descriptors)
    ids = [x.id for x in main_folders]

    # Find all year folders
    year_children = defaultdict(list)
    children = Folder.objects.filter(parent_id__in=ids)
    for x in children:
        # If a year-like folder
        if x.short_name.isdigit():
            year_children[x.parent_id].append(x)

    all_folders = main_folders[:]

    # Pick only last X years for each of the main folders
    for key, value in year_children.iteritems():
        _sorted = sorted(value, key=lambda x: x.name, reverse=True)
        _sorted = _sorted[:settings.FOLDER_INLINE_YEAR_COUNT][::-1]
        year_children[key] = _sorted
        all_folders.extend(_sorted)

    # Get user's statistics for all of these folder. That's the whole
    # purpose of this inline year shortcuts.
    user_stats = Folder.many_get_user_stats(all_folders, user)
    for x in all_folders:
        # Keep only last two digits
        x.t_short_year_name = "'" + x.short_name[-2:]

        stats = user_stats.get(x.id)
        solvable_task_count = stats and stats[1]

        any, any_non_rated, percent, RGB =  \
            Folder.parse_solution_stats(stats and stats[2], solvable_task_count)

        # Main folder
        if any and x.id in year_children:
            plus_sign = '+' if any_non_rated else ''
            x.t_percent_str = mark_safe(
                '<span style="color:#%02X%02X%02X;">(%s%d%%)</span>'    \
                    % (RGB[0], RGB[1], RGB[2], plus_sign, 100 * percent))
        x.t_color = '#%02X%02X%02X' % RGB

    # Stick children to main folders:
    for x in main_folders:
        x.t_year_children = year_children[x.id]

    return {
        'main_folder_chunks': [main_folders[i:i + split]  \
            for i in range(0, len(main_folders), split)],
    }
