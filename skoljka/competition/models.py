import json
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.db.models import F
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy

from skoljka.competition.evaluator import EVALUATOR_V1
from skoljka.mathcontent.models import MathContent
from skoljka.permissions.constants import EDIT
from skoljka.permissions.models import BasePermissionsModel
from skoljka.post.generic import PostGenericRelation
from skoljka.task.models import Task
from skoljka.utils import xss
from skoljka.utils.models import gray_help_text
from skoljka.utils.string_operations import join_urls

KIND_CHOICES = (
    (1, "Competition"),
    (2, "Course"),
)


class Competition(BasePermissionsModel):
    """
    Instructions:
        If using url_path_prefix, you also have to add ID and url prefix to
        COMPETITION_URLS in settings/local.py.
        url_path_prefix must have a leading / if used.
        admin_group must have the VIEW and EDIT permissions for the competition object.
    """

    KIND_COMPETITION = 1
    KIND_COURSE = 2

    name = models.CharField(max_length=64)
    kind = models.SmallIntegerField(default=1, choices=KIND_CHOICES)
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
    fixed_task_score = models.IntegerField(default=0, help_text="Use 0 to disable.")
    min_admin_solved_count = models.IntegerField(
        default=1,
        help_text="Min. required number of admins that solved a task "
        "for it to be published.",
    )
    team_categories = models.CharField(
        blank=True,
        max_length=255,
        help_text="Format is {\"lang\": {\"ID1\": \"name1\", ...}, ...}, "
        "old format is \"ID1:name1 | ID2:name2 | ... \", "
        "where ID is a number. "
        "Last category is considered the default.",
    )
    task_categories_trans = models.CharField(
        blank=False,
        default='',
        max_length=255,
        help_text="Deprecated! Translations of task category names. "
        "E.g. {\"en\": {\"Geometrija\": \"Geometry\"}}. "
        "If a translation is not available, the original name is used.",
    )
    show_solutions = models.BooleanField(
        default=False, help_text="Show solutions after the competition ends."
    )
    public_scoreboard = models.BooleanField(
        default=True,
        help_text="Show scoreboard (for competitions) or the "
        "participants list (for courses) publicly?",
    )

    posts = PostGenericRelation(placeholder=ugettext_lazy("Message"))

    def __unicode__(self):
        return self.name

    def can_send_post(self, user):  # For PostGenericRelation.
        return self.is_user_admin(user)

    def get_absolute_url(self):
        return self.url_path_prefix or '/competition/{}/'.format(self.id)

    def get_registration_url(self):
        # Can this be achieved with Django's URL reversing?
        # (self.url_path_prefix is the problem here...)
        return join_urls(self.get_absolute_url(), 'registration')

    def get_scoreboard_link(self):
        """Return the <a ...>...</a> HTML tag for either the scoreboard (for
        competitions) or the participants list (for courses), with proper
        translation and URL."""
        title = _("Participants") if self.is_course else _("Scoreboard")
        return mark_safe(
            u'<a href="{}/">{}</a>'.format(self.get_scoreboard_url(), xss.escape(title))
        )

    def get_scoreboard_url(self):
        """Return the URL for either the scoreboard (for competitions) or the
        participants list (for courses)."""
        if self.is_course:
            return join_urls(self.get_absolute_url(), 'participants')
        else:
            return join_urls(self.get_absolute_url(), 'scoreboard')

    def get_languages(self):
        """Return the languages this competition is translated to.

        Defines the languages of chain names.
        """
        # Currently hardcoded, should be a DB column.
        # If updating, update the competition_chain_list_tasks.html text about
        # the category input.
        return ['hr', 'en']

    def get_task_categories_translations(self, lang):
        """Return the dictionary of translations for the given language.

        In case of an invalid task_categories_trans field or missing
        translations, an empty dictionary is returned."""
        try:
            return json.loads(self.task_categories_trans)[lang]
        except:  # noqa: E722 do not use bare 'except'
            return {}

    @property
    def is_course(self):
        return self.kind == self.KIND_COURSE

    def is_user_admin(self, user):
        return self.user_has_perm(user, EDIT)

    def msg_has_finished(self):
        if self.is_course:
            return _("Course has finished.")
        else:
            return _("Competition has finished.")

    def msg_has_not_started(self):
        if self.is_course:
            return _("Course has not started yet.")
        else:
            return _("Competition has not started yet.")

    def use_custom_ctask_names(self):
        """Whether CompetitionTask names are determined automatically or are
        manual. For now, manual names are used for and only for courses."""
        return self.kind == self.KIND_COURSE


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

    posts = PostGenericRelation(placeholder=ugettext_lazy("Message"))

    def __unicode__(self):
        return self.name

    def can_send_post(self, user):  # For PostGenericRelation.
        # Only members and admins can post messages to team.posts.
        # Note: Submission.can_send_post relies on this logic.
        if TeamMember.objects.filter(member=user, team=self).exists():
            return True
        return self.competition.is_user_admin(user)

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
        return mark_safe(
            u'<a href="{}" class="{}">{}</a>'.format(
                self.get_absolute_url(),
                self.get_type_css_class(),
                xss.escape(self.name),
            )
        )

    def get_send_notification_link(self):
        url = '{}notifications/admin/?team={}#post'.format(
            self.competition.get_absolute_url(), self.id
        )
        return mark_safe(u'<a href="{}"><i class="icon-envelope"></i></a>'.format(url))


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
    UNLOCK_GRADUAL = 1
    UNLOCK_ALL = 2
    UNLOCK_MODES = (
        (UNLOCK_GRADUAL, ugettext_lazy("Gradual unlocking")),
        (UNLOCK_ALL, ugettext_lazy("All tasks unlocked")),
    )

    competition = models.ForeignKey(Competition)
    name = models.CharField(max_length=200)
    unlock_minutes = models.IntegerField(default=0)

    # Category is currently a string which stores the category name (title),
    # translations and ordering. See views.py for more info. Categories are
    # considered equal if the strings match exactly. In the future, we may
    # consider adding a new model Category. So far this suffices.
    category = models.CharField(blank=True, db_index=True, max_length=200)
    bonus_score = models.IntegerField(default=1)
    position = models.IntegerField(
        default=0, help_text=gray_help_text(ugettext_lazy("Position in the category."))
    )
    unlock_mode = models.SmallIntegerField(choices=UNLOCK_MODES, default=UNLOCK_GRADUAL)
    cache_ctask_comments_info = models.CharField(blank=True, max_length=255)
    cache_is_verified = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return self.competition.get_absolute_url() + 'chain/{}/'.format(self.id)

    @property
    def unlock_days(self):
        return self.unlock_minutes / (24 * 60.0)


class CompetitionTask(models.Model):
    class Meta:
        unique_together = (('competition', 'task'),)

    competition = models.ForeignKey(Competition)
    task = models.ForeignKey(Task)
    descriptor = models.CharField(max_length=255)
    max_submissions = models.IntegerField(default=3)
    max_score = models.IntegerField(default=1)
    chain = models.ForeignKey(Chain, blank=True, null=True)
    chain_position = models.IntegerField(default=0)
    comment = models.OneToOneField(MathContent)
    cache_admin_solved_count = models.IntegerField(default=0)

    cache_new_activities_count = models.IntegerField(
        default=0, help_text="Number of solutions with an ungraded or unread update."
    )

    def __unicode__(self):
        return u"CompetitionTask {} comp={} task={}".format(
            self.get_name(), self.competition_id, self.task_id
        )

    def get_name(self):
        if self.competition.use_custom_ctask_names():
            return self.task.name
        elif self.chain_id:
            return u"{} #{}".format(self.chain.name, self.chain_position)
        else:
            return u"(No chain) id={}".format(self.id)

    def get_absolute_url(self):
        return self.competition.get_absolute_url() + 'task/{}/'.format(self.id)

    def get_edit_url(self):
        return self.get_absolute_url() + 'edit/'

    def get_send_clarification_request_url(self):
        return self.competition.get_absolute_url() + 'notifications/{}/#post'.format(
            self.id
        )

    def get_link(self):
        return mark_safe(
            u'<a href="{}">{}</a>'.format(
                self.get_absolute_url(), xss.escape(self.get_name())
            )
        )

    def is_automatically_graded(self):
        return self.descriptor != settings.COMPETITION_MANUAL_GRADING_TAG

    def is_manually_graded(self):
        return self.descriptor == settings.COMPETITION_MANUAL_GRADING_TAG

    def update_cache_new_activities_count(self, delta):
        """Atomically perform `cache_new_activities_count += delta` in the
        database.

        The local value of `self.cache_new_activities_count` is updated as well,
        but non-atomically and may mismatch the final database value."""
        CompetitionTask.objects.filter(id=self.id).update(
            cache_new_activities_count=F('cache_new_activities_count') + delta
        )
        self.cache_new_activities_count += delta


class Submission(models.Model):
    # Arbitrary point in the past, used as a blank value in
    # `oldest_unseen_admin_activity` in order to avoid having null=True.
    NO_UNSEEN_ACTIVITIES_DATETIME = datetime(year=2000, month=1, day=1)

    ctask = models.ForeignKey(CompetitionTask)
    team = models.ForeignKey(Team)
    date = models.DateTimeField()
    # TODO: Rename `result` to `answer`?
    result = models.CharField(max_length=255)
    content = models.ForeignKey(MathContent, blank=True, null=True)
    score = models.IntegerField(default=0)

    # Note: the team activity date is reset either manually by clicking on
    # "Mark as read" or by grading the solution. The admin activity is reset
    # immediately when viewed.
    oldest_unseen_admin_activity = models.DateTimeField(
        default=NO_UNSEEN_ACTIVITIES_DATETIME
    )
    oldest_unseen_team_activity = models.DateTimeField(
        default=NO_UNSEEN_ACTIVITIES_DATETIME
    )

    posts = PostGenericRelation(placeholder=ugettext_lazy("Message"))

    def save(self, *args, **kwargs):
        # Using auto_add_now would break tests.
        if self.date is None:
            self.date = datetime.now()
        super(Submission, self).save(*args, **kwargs)

    def can_send_post(self, user):  # For PostGenericRelation.
        return self.team.can_send_post(user)

    def get_admin_url(self):
        return '{}submission/{}/'.format(
            self.ctask.competition.get_absolute_url(), self.id
        )

    def get_tr_class(self):
        """Get <tr>...</tr> class in admin submissions list."""
        if self.score == self.ctask.max_score:
            out = ['ctask-correct']
        elif self.score > 0:
            # Only for manually graded tasks.
            out = ['ctask-partially-correct']
        else:
            out = []

        if self.has_new_team_activities():
            out.append('csub-unseen-team-activities')
        return ' '.join(out)

    def has_new_team_activities(self):
        # Note: update refresh_ctask_cache_new_activities_count if this logic
        # is being updated.
        return self.oldest_unseen_team_activity != self.NO_UNSEEN_ACTIVITIES_DATETIME

    def mark_unseen_admin_activity(self):
        """Update oldest_unseen_admin_activity if is not already set. Return
        whether the field was updated. Does not save."""
        if (
            self.oldest_unseen_admin_activity
            == Submission.NO_UNSEEN_ACTIVITIES_DATETIME
        ):
            self.oldest_unseen_admin_activity = datetime.now()
            return True
        else:
            return False

    def mark_unseen_team_activity(self):
        """Update oldest_unseen_team_activity if is not already set.
        Update the competition task's activity counter accordingly.
        Return whether the field was updated. Does not save the submission,
        does update the competition task."""
        if self.oldest_unseen_team_activity == Submission.NO_UNSEEN_ACTIVITIES_DATETIME:
            self.oldest_unseen_team_activity = datetime.now()
            self.ctask.update_cache_new_activities_count(+1)
            return True
        else:
            return False

    def reset_unseen_team_activities(self):
        """Reset oldest_unseen_team_activity.
        Update the corresponding competition task's activity counter.
        Does not save the submission, does update the competition task."""
        if self.has_new_team_activities():
            self.ctask.update_cache_new_activities_count(-1)
            self.oldest_unseen_team_activity = Submission.NO_UNSEEN_ACTIVITIES_DATETIME

    def __unicode__(self):
        return "ctask={} team={} {}".format(self.ctask_id, self.team_id, self.date)
