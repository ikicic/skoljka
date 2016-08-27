from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView

urlpatterns = patterns('',
    (r'^ajax/mathcontent/preview/$', 'mathcontent.ajax.preview'),

    (r'^mathcontent/(?P<id>\d+)/attachments/$', 'mathcontent.views.edit_attachments'),
    (r'^attachment/(?P<id>\d+)/delete/$', 'mathcontent.views.delete_attachment'),
)
