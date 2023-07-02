from django.conf.urls.defaults import patterns

urlpatterns = patterns(
    '',
    (r'^post/add/$', 'skoljka.post.views.add_post'),
    (r'^post/(?P<post_id>\d+)/edit/$', 'skoljka.post.views.edit_post'),
)
