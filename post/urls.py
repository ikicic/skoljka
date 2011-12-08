from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView

urlpatterns = patterns('',
    (r'^post/add/$', 'post.views.add_post'),
    (r'^post/(?P<post_id>\d+)/edit/$', 'post.views.edit_post'),
)
