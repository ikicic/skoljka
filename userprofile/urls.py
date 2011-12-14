from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView, TemplateView

from django.contrib.auth.models import User

urlpatterns = patterns('',
    (r'^memberlist/$', ListView.as_view(
        queryset=User.objects.select_related('profile'),
        context_object_name="user_list",
        template_name="memberlist.html",
    )),

# TODO: vide se skrivene grupe
    (r'^profile/(?P<pk>\d+)/', DetailView.as_view(
        queryset=User.objects.select_related('profile'),
        context_object_name='profile',                # 'user' cannot be used
        template_name='profile_detail.html')),
    
    (r'^register/$', 'userprofile.views.register'),
    (r'^register/complete/', TemplateView.as_view(template_name='registration_complete.html')),
    (r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}),
)
