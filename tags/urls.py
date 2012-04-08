from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('',
    (r'^ajax/tag/add/$', 'tags.ajax.add'),
    (r'^ajax/tag/delete/$', 'tags.ajax.delete'),
    
    (r'^tags/$', 'tags.views.list'),
)
