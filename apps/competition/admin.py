from django.contrib import admin

from competition.models import Chain, Competition, CompetitionTask, Team, \
        TeamMember, Submission
from competition.utils import refresh_teams_cache_score, \
        refresh_submissions_cache_is_correct

class CompetitionAdmin(admin.ModelAdmin):
    actions = ['refresh_submissions_cache_is_correct']

    def save_model(self, request, obj, form, change):
        if obj.fixed_task_score:
            CompetitionTask.objects.filter(competition=obj) \
                                   .update(score=obj.fixed_task_score)
        obj.save()

    def refresh_submissions_cache_is_correct(self, request, queryset):
        result = refresh_submissions_cache_is_correct(competitions=queryset)
        self.message_user(request, "{} submission(s) corrected.".format(result))

class TeamAdmin(admin.ModelAdmin):
    actions = ['refresh_cache_score']

    def refresh_cache_score(self, request, queryset):
        refresh_teams_cache_score(queryset)


class SubmissionAdmin(admin.ModelAdmin):
    actions = ['refresh_cache_is_correct']

    def refresh_cache_is_correct(self, request, queryset):
        result = refresh_submissions_cache_is_correct(queryset)
        self.message_user(request, "{} submission(s) corrected.".format(result))


class CompetitionTaskAdmin(admin.ModelAdmin):
    actions = ['refresh_submissions_cache_is_correct']

    def refresh_submissions_cache_is_correct(self, request, queryset):
        # TODO: move this to the method itself
        submissions = Submission.objects.filter(ctask__in=queryset)
        result = refresh_submissions_cache_is_correct(submissions, queryset)
        self.message_user(request, "{} submission(s) corrected.".format(result))

admin.site.register(Competition, CompetitionAdmin)
admin.site.register(Chain, admin.ModelAdmin)
admin.site.register(CompetitionTask, CompetitionTaskAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TeamMember, admin.ModelAdmin)
admin.site.register(Submission, SubmissionAdmin)
