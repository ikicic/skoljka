"""
    Namespaced cache module. Cache module extension/wrapper.

    Key used to save namespace counter is namespace string itself.

    Term full_key is used for final cache key generated from namespace, its
    counter and given key (i.e. subkey). Note that you need the counter to
    access the final cached value (that's how the namespace mechanism works).

    TODO: details, usage etc.
"""

# For performance reasons, ncache is implemented as a module, not as a class.
# (is it faster that way?)

from django.conf import settings
from django.core.cache import cache

def make_full_key(namespace, counter, key):
    """
        Generate full key from namespace, counter and (sub)key.
    """
    return '{}-{}-{}'.format(namespace, counter, key)

def get_counter(namespace):
    """
        Get counter for given namespace. If not found, returns None.
    """
    # This method is created for low-level external usage. Internally,
    # each ncache method calls cache.get{_many}(...) manually.
    return cache.get(namespace)

def get_counters(namespaces):
    """
        Get counter for each of given namespaces. Returns result as a dict
        {namespace: counter}. Non-existing namespaces are ignored.
    """
    return cache.get_many(namespaces)

def get_or_create_counter(namespace):
    """
        Get counter for given namespace, or create it if it doesn't exist.

        Returns pair:
            counter, is_created
    """
    counter = cache.get(namespace)
    if counter:
        return counter, False

    cache.set(namespace, 1)
    return 1, True

def get(namespace, key, default=None):
    """
        Get cached value for given key and namespace. Returns None in value
        not found.
    """
    counter = cache.get(namespace)
    if not counter:
        return default
    return cache.get(make_full_key(namespace, counter, key), default)

def get_full_key(namespace, key):
    """
        Returns full key for given (sub)key and namespace. If namespace not
        used (i.e. counter doesn't exist), create it.
    """
    counter, dummy = get_or_create_counter(namespace)
    return make_full_key(namespace, counter, key)

def get_many_for_update(namespaces, keys):
    """
        Get cached data together with full_keys used. Prepare for updating, i.e.
        automatically create namespace counters if necessary.

        Returns pair: cached_data, full_keys
            where cached_data is dictionary {full_keys: data}
            and full_keys is a list of full keys, in the same order as
            given namespaces and keys.

        Use cache.set_many({full_key: value}) to finish updating.
        It is assumed namespace counters won't change in between. (if they do,
        maybe it is even better to immediately 'mark' data as invalid...)
    """
    counters = cache.get_many(namespaces)

    # Create new counters
    new_counters = {x: 1 for x in namespaces if x not in counters}
    cache.set_many(new_counters)

    # Generate list of full_keys and list of keys to read from cache.
    full_keys = []
    to_get = []
    for namespace, key in zip(namespaces, keys):
        counter = counters.get(namespace, None)
        if counter:
            full_key = make_full_key(namespace, counter, key)
            full_keys.append(full_key)
            to_get.append(full_key)
        else:
            full_keys.append(make_full_key(namespace, 1, key))

    return cache.get_many(to_get), full_keys

def invalidate_namespace(namespace):
    """
        Invalidate given namespace. Fails silently if namespace doesn't exist.
    """
    try:
        if settings.DEBUG:
            print 'Invalidating namespace "%s"' % namespace
        cache.incr(namespace)
    except ValueError:
        # Cache does not even exist. Ignore.
        pass

def invalidate_namespaces(namespaces):
    """
        Shortcut for invalidating multiple namespaces.
        Depending on cache backend, this could be made more efficient than just
        calling invalidate_namespace multiple times.
    """
    # But for now, it makes no difference.
    for namespace in namespaces:
        invalidate_namespace(namespace)
