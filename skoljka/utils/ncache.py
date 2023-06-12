"""Namespaced cache module. Cache module extension/wrapper.

The key used to save namespace counter is the namespace string itself.

The term full key is used for final cache key generated from namespace, its
counter and given key (i.e. subkey). Note that you need the counter to
access the final cached value (that's how the namespace mechanism works).
"""

from __future__ import print_function

from django.conf import settings
from django.core.cache import cache

def make_full_key(namespace, counter, key):
    """Generate full key from namespace, counter and (sub)key. """
    return '{}-{}-{}'.format(namespace, counter, key)


def get_counter(namespace):
    """Get counter for given namespace. If not found, returns None."""
    # This method is created for low-level external usage. Internally,
    # each ncache method calls cache.get{_many}(...) manually.
    return cache.get(namespace)


def get_counters(namespaces):
    """Get the counter for each of the given namespaces.

    Returns result as a dict {namespace: counter}.
    Non-existing namespaces are ignored.
    """
    return cache.get_many(namespaces)


def get_or_create_counter(namespace):
    """Get counter for given namespace. Create if it doesn't exist yet."""
    # TODO: Switch to cache.get_or_set after upgrading to Django 1.9.
    counter = cache.get(namespace)
    if counter:
        return counter

    cache.set(namespace, 1)
    return 1


def get(namespace, key, default=None):
    """Return the cached value for given key and namespace.

    If the value not found, returns the value given by the 'default' argument,
    which is None by default.
    """
    counter = cache.get(namespace)
    if not counter:
        return default
    return cache.get(make_full_key(namespace, counter, key), default)


def get_full_key(namespace, key):
    """Return full key for given (sub)key and namespace.

    Namespace (i.e. the counter) automatically created if not found.
    """
    counter = get_or_create_counter(namespace)
    return make_full_key(namespace, counter, key)


def get_many_for_update(namespaces, keys):
    """Get cached data, full keys and create namespace counter where necessary.

    Arguments namespaces and keys should be a lists of the same size.

    Returns a pair (cached_data, full_keys),
        where cached_data is a dictionary {full_keys: data}
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


def invalidate_full_key(full_key):
    """Invalidate given namespace.

    Use with caution, be sure to use the latest namespace counter!
    """
    if settings.DEBUG:
        print("Invalidating full key \"%s\"" % full_key)  # TODO: log
    cache.delete(full_key)


def invalidate_namespace(namespace):
    """Invalidate given namespace."""
    try:
        if settings.DEBUG:
            print("Invalidating namespace \"%s\"" % namespace)  # TODO: log
        cache.incr(namespace)
    except ValueError:
        pass  # Cache does not exist. Ignore.


def invalidate_namespaces(namespaces):
    """Invalidate multiple namespaces.

    Depending on cache backend, this could be made more efficient than just
    calling invalidate_namespace multiple times. Currently we invalidate one
    namespace at a time.
    """
    for namespace in namespaces:
        invalidate_namespace(namespace)
