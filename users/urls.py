from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
    # TODO change name
    (r'^$', 'users.views.login_view'),
)

