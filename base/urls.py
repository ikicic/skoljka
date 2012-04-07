from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

# You probably shouldn't add anything here as only unqualified requests
# get here.

urlpatterns = patterns('',
    (r'^$', 'base.views.homepage'),
#    (r'robots\.txt$', direct_to_template, {'template': 'robots.txt', 'mimetype': 'text/plain'}),

    (r'^help/$', 'base.views.help'),
)
