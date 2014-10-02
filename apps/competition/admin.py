from django.contrib import admin

from competition.models import Chain, Competition, CompetitionTask, Team, \
        TeamMember, Submission
from competition.utils import refresh_cache_score_for_teams

class TeamAdmin(admin.ModelAdmin):
    actions = ['refresh_cache_score']

    def refresh_cache_score(self, request, queryset):
        refresh_cache_score_for_teams(queryset)



admin.site.register(Competition, admin.ModelAdmin)
admin.site.register(Chain, admin.ModelAdmin)
admin.site.register(CompetitionTask, admin.ModelAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TeamMember, admin.ModelAdmin)
admin.site.register(Submission, admin.ModelAdmin)

