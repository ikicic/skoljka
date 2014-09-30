from django.contrib import admin

from competition.models import Chain, Competition, CompetitionTask, Team, \
        TeamMember

class CompetitionAdmin(admin.ModelAdmin):
    pass

admin.site.register(Competition, CompetitionAdmin)

admin.site.register(Chain, admin.ModelAdmin)
admin.site.register(CompetitionTask, admin.ModelAdmin)
admin.site.register(Team, admin.ModelAdmin)
admin.site.register(TeamMember, admin.ModelAdmin)

