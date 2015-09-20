from django.contrib import admin

from competition.models import Chain, Competition, CompetitionTask, Team, \
        TeamMember, Submission
from competition.utils import refresh_teams_cache_score, \
        refresh_submissions_cache_is_correct

class CompetitionAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if obj.fixed_task_score:
            CompetitionTask.objects.filter(competition=obj) \
                                   .update(score=obj.fixed_task_score)
        obj.save()

class TeamAdmin(admin.ModelAdmin):
    actions = ['refresh_cache_score']

    def refresh_cache_score(self, request, queryset):
        refresh_teams_cache_score(queryset)


class SubmissionAdmin(admin.ModelAdmin):
    actions = ['refresh_cache_is_correct']

    def refresh_cache_is_correct(self, request, queryset):
        refresh_submissions_cache_is_correct(queryset)


class CompetitionTaskAdmin(admin.ModelAdmin):
    actions = ['refresh_submissions_correctness']

    def refresh_submissions_correctness(self, request, queryset):
        submissions = Submission.objects.filter(ctask__in=queryset)
        refresh_submissions_cache_is_correct(submissions, queryset)

admin.site.register(Competition, CompetitionAdmin)
admin.site.register(Chain, admin.ModelAdmin)
admin.site.register(CompetitionTask, CompetitionTaskAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TeamMember, admin.ModelAdmin)
admin.site.register(Submission, SubmissionAdmin)
