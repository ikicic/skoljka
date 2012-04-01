from functools import wraps
from django.contrib.auth.decorators import login_required
from django.db.models.signals import pre_save
from django.db.models.signals import post_save
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponsePermanentRedirect, HttpResponseNotAllowed
from django.template import loader, RequestContext

# TODO: add login check
def require(method=[], ajax=None, post=[], get=[]):
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
    return require(ajax=True, *args, **kwargs)


# this is a decorator
class response:
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
                return HttpResponse(x)

            status = None
            content = None
            
            template = self.template
            # is any of special types
            if isinstance(x, dict):         # use default template
                status = 200
                content = x
            elif isinstance(x, (int, long)):  # empty content, status code defined
                status = x
                content = ''
            elif isinstance(x, tuple):        # given a tuple
                # len == 1 -> redirect
                # len == 2 -> status (int), content (string / dict)
                # len == 3 -> status (int), template (string), content (string / dict)
                if len(x) == 1:
                    return HttpResponseRedirect(x[0])
                if len(x) == 2:
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
                content = loader.render_to_string(template, content, context_instance=RequestContext(request))
                
            if content is not None:                
                if status == response.REDIRECT:
                    return HttpResponseRedirect(content)
                elif status == response.MOVED:
                    return HttpResponsePermanentRedirect(content)
                else:
                    return HttpResponse(content, status=status)
                
            # can't recognize data, return original
            return x
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

