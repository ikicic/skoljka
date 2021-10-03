from django.conf import settings
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

_EXTRA_URLS = [(x[0], direct_to_template, {'template': x[1]}) for x in settings.EXTRA_BASE_URLS]

js_info_dict = {
    'packages': ('competition', ),
}


urlpatterns = patterns('',
    (r'^$', 'base.views.homepage'),
    (r'^robots\.txt$', direct_to_template, {'template': 'robots.txt', 'mimetype': 'text/plain'}),

    (r'^help/$', direct_to_template, {'template': 'help/help.html'}),
    (r'^help/folders/$', direct_to_template, {'template': 'help/help_folders.html'}),
    (r'^help/format/$', 'base.help.help_format'),
    (r'^help/instructions/$', direct_to_template, {'template': 'help/help_instructions.html'}),
    (r'^help/other/$', direct_to_template, {'template': 'help/help_other.html'}),
    (r'^help/permissions/$', direct_to_template, {'template': 'help/help_permissions.html'}),
    (r'^help/upload/$', direct_to_template, {'template': 'help/help_upload.html'}),

    (r'^about/$', direct_to_template, {'template': 'about.html'}),
    (r'^featured_lecture/', 'base.views.featured_lecture'),
    (r'^tou/$', direct_to_template, {'template': 'terms_of_use.html'}),

    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^jsi18n/$', 'base.views.cached_javascript_catalog', js_info_dict),

    *_EXTRA_URLS
)

