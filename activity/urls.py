from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'activity.views.list'),
)
