import re

# [order=-10] asdf --> ('-10', ' asdf')
_CATEGORY_RE = re.compile(r'\[order=([-+]?\d+)\](.+)')


class ChainCategory(object):
    """
    Helper class representing a chain category.

    Attribute `name` is a string of one of the following formats:
        "name"
        "name for language 1 | name for language 2"
        "[order=123] name"
        "[order=123] name | name"              <-- same order for all languages
        "[order=123] name | [order=132] name"  <-- custom order per language

    The order number may be negative.
    """

    def __init__(self, name, competition, lang, category_translations):
        translated_name = pick_name_translation(name, competition, lang)
        order, translated_name = self.split_order_name(translated_name)
        if order is None:
            # If there was no [order=...] for the current language, check if it
            # was specified for the first language.
            order, _ = self.split_order_name(name)
            if order is None:
                order = 0

        translated_name = translated_name.strip()
        if category_translations:  # Legacy, deprecated.
            translated_name = category_translations.get(
                translated_name, translated_name
            )

        self.name = name
        self.order = order
        self.translated_name = translated_name
        self.chains = []
        self.t_is_locked = None

    @property
    def sort_key(self):
        return (self.order, self.translated_name)

    @staticmethod
    def split_order_name(name):
        """Split a string "[order=213] Name" into a tuple (123, "Name").

        If there is no valid "[order=...]" prefix, (None, name) is returned
        instead.
        """
        match = _CATEGORY_RE.match(name)
        if match:
            try:
                order, name = match.groups()
                order = int(order)
                return order, name
            except:  # noqa: E722 do not use bare 'except'
                pass
        return None, name


def init_categories_and_sort_chains(
    competition, chains, language_code, sort_by='category', sort_descending=False
):
    """Find unique categories, fill chain.t_category and sort chains.

    Attributes:
        chains: a sequence of Chain objects
        competition: a Competition object
        language_code: an optional string representing the language
        sort_by: 'category' or 'unlock_minutes', 'category' by default
        sort_descending: whether to sort in the reverse order, False by default

    Returns a tuple (sorted categories list, sorted chains list).
    Note that if chains are not sorted according to the category, the category
    sorting will be unrelated to the sorting of chains.
    """
    chains = list(chains)

    # First sort by position and name, such that they are appended to
    # categories in the correct order.
    chains.sort(key=lambda chain: (chain.position, chain.name))

    # Deprecated.
    category_translations = competition.get_task_categories_translations(language_code)

    categories = {}
    for chain in chains:
        category = categories.get(chain.category)
        if not category:
            category = categories[chain.category] = ChainCategory(
                chain.category, competition, language_code, category_translations
            )
        chain.t_category = category
        category.chains.append(chain)

    # Once categories are known, sort either by categories or by
    # unlock_minutes. The sort is stable.
    if sort_by == 'unlock_minutes':
        chains.sort(key=lambda chain: chain.unlock_minutes)
    else:
        chains.sort(key=lambda chain: chain.t_category.sort_key)

    categories = list(categories.values())
    categories.sort(key=lambda cat: cat.sort_key)

    if sort_descending:
        chains = chains[::-1]
        categories = categories[::-1]

    return categories, chains


def pick_name_translation(name, competition, lang):
    """Pick the correct chain or category name translation.

    Parse a string of form "translation1 | ... | translationN" and pick the
    translation matching the current language. The order of languages is
    defined at the competition level.

    The original string is returned if
        - the current language does not match any competition language, or
        - the number of translations in `name` does not match the number of
          competition languages.
    """
    languages = competition.get_languages()
    try:
        index = languages.index(lang)
    except ValueError:
        return name
    translations = name.split('|')
    if len(translations) != len(languages):
        return name
    return translations[index].strip()
