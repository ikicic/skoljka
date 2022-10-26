from django.contrib import admin

from skoljka.competition.models import Chain, Competition, CompetitionTask, \
        Team, TeamMember, Submission
from skoljka.competition.utils import refresh_teams_cache_score, \
        refresh_submissions_score

class CompetitionAdmin(admin.ModelAdmin):
    actions = ['refresh_submissions_score']

    def save_model(self, request, obj, form, change):
        if obj.fixed_task_score:
            CompetitionTask.objects.filter(competition=obj) \
                                   .update(max_score=obj.fixed_task_score)
        obj.save()

    def refresh_submissions_score(self, request, queryset):
        result = refresh_submissions_score(competitions=queryset)
        self.message_user(request, "{} submission(s) corrected.".format(result))


class TeamAdmin(admin.ModelAdmin):
    actions = ['refresh_cache_score']

    def refresh_cache_score(self, request, queryset):
        refresh_teams_cache_score(queryset)


class SubmissionAdmin(admin.ModelAdmin):
    actions = ['refresh_score']

    def refresh_score(self, request, queryset):
        result = refresh_submissions_score(queryset)
        self.message_user(request, "{} submission(s) corrected.".format(result))


class CompetitionTaskAdmin(admin.ModelAdmin):
    actions = ['refresh_submissions_score']

    def refresh_submissions_score(self, request, queryset):
        # TODO: move this to the method itself
        submissions = Submission.objects.filter(ctask__in=queryset)
        result = refresh_submissions_score(submissions, queryset)
        self.message_user(request, "{} submission(s) corrected.".format(result))


admin.site.register(Competition, CompetitionAdmin)
admin.site.register(Chain, admin.ModelAdmin)
admin.site.register(CompetitionTask, CompetitionTaskAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TeamMember, admin.ModelAdmin)
admin.site.register(Submission, SubmissionAdmin)
