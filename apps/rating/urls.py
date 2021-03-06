from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('',
    (r'^ajax/rating/vote/(?P<object_id>\d+)/(?P<content_type_id>\d+)/(?P<name>[a-z_]+)/', 'rating.ajax.vote'),

    # move to tags/ajax.py?
    (r'^ajax/tag/vote/', 'rating.ajax.tag_vote'),
)
