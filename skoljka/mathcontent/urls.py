from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView

urlpatterns = patterns('',
    (r'^ajax/mathcontent/preview/$', 'skoljka.mathcontent.ajax.preview'),

    (r'^mathcontent/(?P<id>\d+)/attachments/$', 'skoljka.mathcontent.views.edit_attachments'),
)
