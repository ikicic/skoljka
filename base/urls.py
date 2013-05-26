from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

# You probably shouldn't add anything here as only unqualified requests
# get here.

urlpatterns = patterns('',
    (r'^$', 'base.views.homepage'),
    (r'^robots\.txt$', direct_to_template, {'template': 'robots.txt', 'mimetype': 'text/plain'}),

    (r'^help/$', direct_to_template, {'template': 'help/help.html'}),
    (r'^help/folders/$', direct_to_template, {'template': 'help/help_folders.html'}),
    (r'^help/instructions/$', direct_to_template, {'template': 'help/help_instructions.html'}),
    (r'^about/$', direct_to_template, {'template': 'about.html'}),
)
