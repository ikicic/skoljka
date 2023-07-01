from django.conf.urls.defaults import include, patterns, url
from django.views.generic import DetailView, ListView, TemplateView

urlpatterns = patterns(
    '',
    (r'^post/add/$', 'skoljka.post.views.add_post'),
    (r'^post/(?P<post_id>\d+)/edit/$', 'skoljka.post.views.edit_post'),
)
