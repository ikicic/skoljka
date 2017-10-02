from django.contrib.auth.models import User, Group
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from libs.string_operations import join_urls

from competition.evaluator import EVALUATOR_V1
from mathcontent.models import MathContent
from permissions.constants import EDIT
from permissions.models import BasePermissionsModel
from post.generic import PostGenericRelation
from task.models import Task

from skoljka.libs import xss
from skoljka.libs.models import gray_help_text

from datetime import datetime
import re

class Competition(BasePermissionsModel):
    """
    Instruction:
        If using url_path_prefix, you also have to add ID and url prefix to
        COMPETITION_URLS in settings/local.py.
        url_path_prefix must have leading / if used.
        admin_group must have VIEW and EDIT permissions for the competition
        object.
    """
    name = models.CharField(max_length=64)
    hidden = models.BooleanField(default=True)
    registration_open_date = models.DateTimeField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    default_max_submissions = models.IntegerField(default=3)
    max_team_size = models.IntegerField(default=3)
    admin_group = models.ForeignKey(Group, blank=True, null=True)
    automatic_task_tags = models.CharField(blank=True, max_length=64)
    description_template_filename = models.CharField(blank=True, max_length=255)
    rules_template_filename = models.CharField(blank=True, max_length=255)
    url_path_prefix = models.CharField(blank=True, max_length=64)
    scoreboard_freeze_date = models.DateTimeField()
    evaluator_version = models.IntegerField(default=EVALUATOR_V1)
    fixed_task_score = models.IntegerField(default=0,
            help_text="Use 0 to disable.")
    min_admin_solved_count = models.IntegerField(default=1,
            help_text="Min. required number of admins that solved a task "
                      "for it to be published.")
    team_categories = models.CharField(
            blank=True, max_length=255,
            help_text="Format: \"ID1:name1 | ID2:name2 | ... \". " \
                      "Last category is considered the default.")
    show_solutions = models.BooleanField(
            default=False,
            help_text="Show solutions after the competition ends.")

    posts = PostGenericRelation(placeholder="Poruka")

    def __unicode__(self):
        return self.name

    def can_send_post(self, user): # PostGenericRelation
        return self.user_has_perm(user, EDIT)

    def get_absolute_url(self):
        return self.url_path_prefix or '/competition/{}/'.format(self.id)

    def get_registration_url(self):
        # Can this be achieved with Django's URL reversing?
        # (self.url_path_prefix is the problem here...)
        return join_urls(self.get_absolute_url(), 'registration')

    def get_scoreboard_url(self):
        return join_urls(self.get_absolute_url(), 'scoreboard')



class Team(models.Model):
    TYPE_NORMAL = 0
    TYPE_UNOFFICIAL = 1
    TYPE_ADMIN_PRIVATE = 2

    name = models.CharField(max_length=40)
    author = models.ForeignKey(User)
    competition = models.ForeignKey(Competition)
    cache_score = models.IntegerField(default=0, db_index=True)
    cache_score_before_freeze = models.IntegerField(default=0, db_index=True)
    cache_max_score_after_freeze = models.IntegerField(default=0)
    team_type = models.IntegerField(default=TYPE_NORMAL)
    category = models.IntegerField(default=0)

    posts = PostGenericRelation(placeholder="Poruka")

    def __unicode__(self):
        return self.name

    def can_send_post(self, user): # PostGenericRelation
        # Only members and and admins can post messages to team.posts.
        if TeamMember.objects.filter(member=user, team=self).exists():
            return True
        return self.competition.user_has_perm(user, EDIT)

    def get_absolute_url(self):
        return self.competition.get_absolute_url() + 'team/{}/'.format(self.id)

    def is_normal(self):
        return self.team_type == Team.TYPE_NORMAL

    def is_admin_private(self):
        return self.team_type == Team.TYPE_ADMIN_PRIVATE

    def get_type_css_class(self):
        if self.team_type == Team.TYPE_UNOFFICIAL:
            return 'comp-unofficial-team'
        if self.team_type == Team.TYPE_ADMIN_PRIVATE:
            return 'comp-admin-private-team'
        return ''

    def get_link(self):
        return mark_safe(u'<a href="{}" class="{}">{}</a>'.format(
                self.get_absolute_url(), self.get_type_css_class(),
                xss.escape(self.name)))

    def get_send_notification_link(self):
        url = '{}notifications/admin/?team={}#post'.format(
                self.competition.get_absolute_url(), self.id)
        return mark_safe(
                u'<a href="{}"><i class="icon-envelope"></i></a>'.format(url))



class TeamMember(models.Model):
    team = models.ForeignKey(Team)
    member = models.ForeignKey(User, blank=True, null=True)
    member_name = models.CharField(max_length=64)
    is_selected = models.BooleanField(default=True)

    INVITATION_UNANSWERED = 0
    INVITATION_ACCEPTED = 1
    INVITATION_DECLINED = 2
    invitation_status = models.IntegerField(default=INVITATION_UNANSWERED)

    def __unicode__(self):
        return self.team.name + '::' + self.member_name



class Chain(models.Model):
    competition = models.ForeignKey(Competition)
    name = models.CharField(max_length=40)
    unlock_minutes = models.IntegerField(default=0)
    category = models.CharField(blank=True, db_index=True, max_length=32)
    bonus_score = models.IntegerField(default=1)
    position = models.IntegerField(default=0,
            help_text=gray_help_text(_("Position in the category.")))
    cache_ctask_comments_info = models.CharField(blank=True, max_length=255)
    cache_is_verified = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return self.competition.get_absolute_url() + 'chain/{}/'.format(self.id)



class CompetitionTask(models.Model):
    class Meta:
        unique_together = (('competition', 'task'), )
    competition = models.ForeignKey(Competition)
    task = models.ForeignKey(Task)
    descriptor = models.CharField(max_length=255)
    max_submissions = models.IntegerField(default=3)
    score = models.IntegerField(default=1)
    chain = models.ForeignKey(Chain, blank=True, null=True)
    chain_position = models.IntegerField(default=0)
    comment = models.OneToOneField(MathContent)
    cache_admin_solved_count = models.IntegerField(default=0)

    def __unicode__(self):
        return u"CompetitionTask {} comp={} task={}".format(
                self.get_name(), self.competition_id, self.task_id)

    def get_name(self):
        if self.chain_id:
            return u"{} #{}".format(self.chain.name, self.chain_position)
        else:
            return u"(No chain) id={}".format(self.id);

    def get_absolute_url(self):
        return self.competition.get_absolute_url() + 'task/{}/'.format(self.id)

    def get_edit_url(self):
        return self.get_absolute_url() + 'edit/'

    def get_send_clarification_request_url(self):
        return self.competition.get_absolute_url() + \
                'notifications/{}/#post'.format(self.id)

    def get_link(self):
        return mark_safe(u'<a href="{}">{}</a>'.format(
                self.get_absolute_url(), xss.escape(self.get_name())))



class Submission(models.Model):
    ctask = models.ForeignKey(CompetitionTask)
    team = models.ForeignKey(Team)
    date = models.DateTimeField()
    result = models.CharField(max_length=255)
    cache_is_correct = models.BooleanField()

    def save(self, *args, **kwargs):
        # Using auto_add_now would break tests.
        if self.date is None:
            self.date = datetime.now()
        super(Submission, self).save(*args, **kwargs)

    def __unicode__(self):
        return "ctask={} team={} {}".format(
                self.ctask_id, self.team_id, self.date)
