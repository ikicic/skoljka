from django.contrib.auth.decorators import login_required

# Don't forget to use same cache as in ncache...
from django.core.cache import cache
from django.db import models
from django.db.models.signals import pre_save
from django.db.models.signals import post_save
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, HttpResponsePermanentRedirect, HttpResponseNotAllowed
from django.template import loader, RequestContext

from skoljka.utils import ncache

from hashlib import sha1
from functools import wraps


def _key_list(input):
    """
        Helper function. Replace models with their primary keys.
    """
    return [(x.pk if isinstance(x, models.Model) else x) for x in input]

def _key_dict(input):
    """
        Helper function. Replace models with their primary keys.
    """
    return {key: str(value.pk if isinstance(value, models.Model) else value)
        for key, value in input.iteritems()}

def cache_function(key=None, namespace=None, seconds=86400*7):
    """
        Cache the result of a function call.

        Parameters:
            key: Cache key format.
            namespace: Format of namespace used. E.g. 'Folder{0.pk}'
                will be converted to Folder5 if function's first parameter
                is a model with .pk == 5.
            seconds: Specify how long this cache should be valid.

        Parameters are called 'key' & 'namespace', not 'key_format' &
        'namespace_format' for DRY reasons.

        Note that it is possible to set both namespace and key format.
        In that case, key is considered as a 'subkey'.

        There are no special option to define key and namespace independent
        of function arguments. Just use key and namespace without any
        curly brackets instead.
    """

    def decorator(func):
        def inner(*args, **kwargs):
            # _key stands for final/full key
            if key:
                _key = key.format(*args)
            else:
                if namespace:
                    # Don't unnecesarry put module name here.
                    # If you need it for any reason, feel free to put it.
                    _key = '{}{}{}'.format(func.__name__, _key_list(args),
                        _key_dict(kwargs))
                else:
                    # If no namespace given, distinguish different modules.
                    _key = '{}{}{}{}'.format(func.__module__, func.__name__,
                        _key_list(args), _key_dict(kwargs))

                # Memcached doesn't like ascii <= 32 and ascii == 127.
                # Just hash it.
                _key = sha1(_key).hexdigest()

            if namespace:
                _namespace = namespace.format(*args)
                _key = ncache.get_full_key(_namespace, _key)

            # Check if value cached. If not, retrieve and save it.
            result = cache.get(_key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(_key, result, seconds)
            return result
        return wraps(func)(inner)
    return decorator

def cache_many_function(namespace_format=None, key_format=None, pre_test=None):
    """
        Handles special case of multiple-get functions.

        Wrapper around functions of type
            def some_many_function(objects, *args)
        where `objects` is a list of object instances(!), and the result is
        a dictionary {object.id: some object info}.

        Generates namespaces, keys and full keys for each object in the objects
        list. Checks which results are already cached, and calls given function
        for the rest, if any. Function will not be called if all results
        are found in the cache.

        Both namespace and key format can be dependend on the object and args
        (in terms of str.format() method).
        E.g. namespace = namespace_format.format(object.id, *args)

        Additional optional parameters:

        pre_test: Function to call with objects and *args before *any* work
            is done. Must return pair
                (should_continue, result_if_not_continuing)

            Example:
                pre_test=lambda objects, user: (user.is_authenticated(), {})
                This method prevents accessing the cache and calling the
                main function if user is not authenticated, in which case it
                just returns {}.
    """

    def decorator(func):
        def inner(objects, *args):
            if pre_test:
                ok, not_ok_value = pre_test(objects, *args)
                if not ok:
                    return not_ok_value

            # Get all namespaces and keys and check cache
            namespaces = [namespace_format.format(x, *args) for x in objects]
            keys = [key_format.format(x, *args) for x in objects]
            cached, full_keys = ncache.get_many_for_update(namespaces, keys)

            # Most common case, handle immediately:
            if len(keys) == len(cached):
                return {x.id: cached[full_key]
                    for x, full_key in zip(objects, full_keys)}

            result = {}
            eval = []
            keys = []
            for x, full_key in zip(objects, full_keys):
                if full_key in cached:
                    # ok, we have this result
                    result[x.id] = cached[full_key]
                else:
                    # not ok, but we are going to ask for it.
                    result[x.id] = full_key # temporary put key here
                    eval.append(x)

            # Evaluate function for objects whose function value not cached
            values = func(eval, *args)

            # Update cache. Here result[id] is the full_key. Not any special
            # reason why we use the same dict `result` for full_keys.
            cache.set_many({result[id]: value
                for id, value in values.iteritems()})

            # Finally, update result (replace those full_keys with results)
            result.update(values)

            return result

        return wraps(func)(inner)
    return decorator

# TODO: add login check
def require(method=[], ajax=None, post=[], get=[], force_login=True):
    """
        TODO

        If force_login is set to True, require will return ResponseForbidden
        if user not logged in.
    """

    if isinstance(method, basestring):
        method = [method]
    if isinstance(post, basestring):
        post = [post]
    if isinstance(get, basestring):
        get = [get]

    # default value of method
    if post and not method:
        method = ['POST']
    if not method:
        method = ['GET']

    def decorator(func):
        def inner(request, *args, **kwargs):
            if ajax is not None:
                if ajax and not request.is_ajax():
                    return HttpResponseBadRequest('Ajax only!')
                elif not ajax and request.is_ajax():
                    return HttpResponseBadRequest('Ajax not allowed!')

            if force_login is not None:
                if force_login and not request.user.is_authenticated():
                    return HttpResponseForbidden('Login first!')
                elif not force_login and request.user.is_authenticated():
                    return HttpResponseForbidden('No registered users allowed!')

            if request.method not in method:
                return HttpResponseNotAllowed(method)

            if get:
                for x in get:
                    if x not in request.GET:
                        return HttpResponseBadRequest('Missing GET "%s" field!' % x)
            if post:
                for x in post:
                    if x not in request.POST:
                        return HttpResponseBadRequest('Missing POST "%s" field!' % x)


            output = func(request, *args, **kwargs)
            if isinstance(output, basestring):
                return HttpResponse(output)
            return output
        return wraps(func)(inner)
    return decorator


def ajax(*args, **kwargs):
    """
        Shortcut for @require, with default parameters:
            ajax=True
            force_login=True
    """

    return require(ajax=True, force_login=kwargs.get('force_login', True), *args, **kwargs)


def response_update_cookie(request, name, value):
    """
        Push cookie update to request.
        MUST be used together with @response, as it will
        do the update before the respond.
    """
    if not hasattr(request, '_response_update_cookies'):
        request._response_update_cookies = {}
    request._response_update_cookies[name] = value


def _flush_cookie_update(request, response):
    if not hasattr(request, '_response_update_cookies'):
        return response
    for key, value in request._response_update_cookies.iteritems():
        response.set_cookie(str(key), str(value))
    return response

# this is a decorator
class response:
    # TODO: implement as function with self.(constants) ?
    """
        Views helper and shortcut decorator.

        Flushes cookie update, pushed by response_update_cookie!
        (only on status OK and redirects)

        Primary shortcut for
            return render_to_response(template, {
                dictionary
            }, context_instance=RequestContext(request))


        Parameter:
            Takes an optional parameter template, path and filename to template.
            Response decorator must be initialized!
            NOT VALID:
                @response
                def detail(request):
                    return 'This is response'

            VALID:
                @response()
                def detail(request):
                    return 'This is response'


        Possible return values:
        - dict:
            Dictionary given to template renderer. Template parameter
            must be given!
        - string:
            Return string as is, with status code 200 OK.
        - int:
            TODO: Return *default* response (...) (i.e. some message)
            Return empty response with given status code.
            If given value is 404, it will raise Http404.
        - tuple:
            There are four different formats:
            - (string, ) - Redirects to given url.
            - (int, content) - Returns content with given status code.
            - (string, content) - Returns content with given template.
            - (int, string, content) - Returns content with given
                template and status code.

            Here `content` denotes string or dict.
                If a string is given, just return it as is.
                In case of a dict, it is passed to a template renderer.

        Additional, template filename can be passed via dict as a 'TEMPLATE' element.


        Examples:
        @response('template_name.html')
        def view(request, some_parameter, another_parameter=None):
            return {'a': 1, 'b': 2}

        @response('default_template.html')
        def view(request, id):
            obj = get_object_or_404(Object, id=id)
            if obj.hidden and obj.author != request.user:
                # returns 403 Forbidden
                return (403, 'Object %d is hidden' % id)

            if (...something...):
                # redirects to Edit page
                return ('/obj/%d/edit/' % id, )

            if (...something else...):
                # everything OK, but use another template
                return ('specific_template.html', {'obj': obj})

            return {'obj': obj}
    """

    OK = 200
    BAD_REQUEST = 400
    FORBIDDEN = 403
    # NOT_FOUND = 404        # raise Http404 or return HttpResponse?
    MOVED = 301
    REDIRECT = 302
    INTERNAL_ERROR = 500
    NOT_IMPLEMENTED = 501

    def __init__(self, template=None):
        self.template = template

    def __call__(self, func):
        def inner(request, *args, **kwargs):
            x = func(request, *args, **kwargs)
            if isinstance(x, basestring):
                return _flush_cookie_update(request, HttpResponse(x))

            status = None
            content = None

            template = self.template
            # is any of special types
            if isinstance(x, dict):         # use default template
                status = 200
                content = x
            elif isinstance(x, (int, long)):  # empty content, status code defined
                if x == 404:
                    raise Http404
                status = x
                content = ''
            elif isinstance(x, tuple):        # given a tuple
                # len == 1 -> redirect
                # len == 2 -> status (int), content (string / dict)
                # len == 3 -> status (int), template (string), content (string / dict)
                if len(x) == 1:
                    return _flush_cookie_update(request, HttpResponseRedirect(x[0]))
                elif len(x) == 2:
                    dummy, content = x
                    if isinstance(dummy, basestring):
                        template = dummy
                    else:
                        status = dummy
                elif len(x) == 3:
                    status, template, content = x

            # render to string if given a dict
            if isinstance(content, dict):
                template = template or content.pop('TEMPLATE', None)
                content = loader.render_to_string(template, content,
                    context_instance=RequestContext(request))

            if content is not None:
                if status == response.REDIRECT:
                    rsp = HttpResponseRedirect(content)
                elif status == response.MOVED:
                    rsp = HttpResponsePermanentRedirect(content)
                else:
                    rsp = HttpResponse(content, status=status)
            else:
                # can't recognize data, return original
                rsp = x


            if isinstance(rsp, HttpResponse) and status in (response.OK,
                    response.MOVED, response.REDIRECT):
                return _flush_cookie_update(request, rsp)
            return rsp
        return wraps(func)(inner)


# http://djangosnippets.org/snippets/2124/
def autoconnect(cls):
    """
    Class decorator that automatically connects pre_save / post_save signals on
    a model class to its pre_save() / post_save() methods.

    # Example usage
    @autoconnect
    class MyModel(models.Model):
        foo = CharField(max_length=10,null=True,blank=True)
        bar = BooleanField()

        def pre_save(self):
            if self.foo is not None:
                self.bar = True
    """
    def connect(signal, func):
        cls.func = staticmethod(func)
        @wraps(func)
        def wrapper(sender, **kwargs):
            return func(kwargs.get('instance'))
        signal.connect(wrapper, sender=cls)
        return wrapper

    if hasattr(cls, 'pre_save'):
        cls.pre_save = connect(pre_save, cls.pre_save)

    if hasattr(cls, 'post_save'):
        cls.post_save = connect(post_save, cls.post_save)

    return cls

