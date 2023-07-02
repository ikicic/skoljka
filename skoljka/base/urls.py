from django.conf import settings
from django.conf.urls.defaults import include, patterns
from django.views.generic import TemplateView

from skoljka.base.views_test import IS_TESTDB

_EXTRA_URLS = [
    (x[0], TemplateView.as_view(template_name=x[1])) for x in settings.EXTRA_BASE_URLS
]

js_info_dict = {
    'packages': ('competition',),
}

# TODO: Remove after switching to Django 1.5, use TemplateView.as_view(..., content_type=...).
# https://stackoverflow.com/questions/6867468/setting-up-mimetype-when-using-templateview-in-django
class TextTemplateView(TemplateView):
    def render_to_response(self, context, **response_kwargs):
        response_kwargs['content_type'] = 'text/plain'
        return super(TemplateView, self).render_to_response(context, **response_kwargs)


urlpatterns = patterns(
    '',
    (r'^$', 'skoljka.base.views.homepage'),
    (r'^robots\.txt$', TextTemplateView.as_view(template_name='robots.txt')),
    (r'^help/$', TemplateView.as_view(template_name='help/help.html')),
    (r'^help/folders/$', TemplateView.as_view(template_name='help/help_folders.html')),
    (r'^help/format/$', 'skoljka.base.help.help_format'),
    (
        r'^help/instructions/$',
        TemplateView.as_view(template_name='help/help_instructions.html'),
    ),
    (r'^help/other/$', TemplateView.as_view(template_name='help/help_other.html')),
    (
        r'^help/permissions/$',
        TemplateView.as_view(template_name='help/help_permissions.html'),
    ),
    (r'^help/upload/$', TemplateView.as_view(template_name='help/help_upload.html')),
    (r'^about/$', TemplateView.as_view(template_name='about.html')),
    (r'^featured_lecture/', 'skoljka.base.views.featured_lecture'),
    (r'^tou/$', TemplateView.as_view(template_name='terms_of_use.html')),
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^jsi18n/$', 'skoljka.base.views.cached_javascript_catalog', js_info_dict),
    *_EXTRA_URLS
)

if IS_TESTDB:
    urlpatterns += patterns(
        '',
        (r'^test/resetdb/', 'skoljka.base.views_test.reset_testdb'),
        (r'^test/latest_email/', 'skoljka.base.views_test.get_latest_email'),
    )
