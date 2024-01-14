import json
from collections import OrderedDict
from datetime import datetime
from enum import Enum

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
from skoljka.utils.python23 import basestring
from skoljka.utils.string_operations import join_urls

KIND_CHOICES = [
    (1, ugettext_lazy("Competition")),
    (2, ugettext_lazy("Course")),
]


class Scoreboard(Enum):
    ALL = 0
    ALL_AND_NONZERO_MY = 1
    ALL_AND_NONZERO_EACH = 2
    ALL_AND_NONZERO_MY_THEN_REST = 3


class RulesTerminology(Enum):
    RULES = 1
    INSTRUCTIONS = 2


_SCOREBOARD = {item.name: item for item in Scoreboard}


class TeamCategories(object):
    """
    Parsed representation of `Competition.team_categories`.

    Attributes:
        lang_to_categories: a dictionary {str lang: OrderedDict{int id: str name}}
        configurable: whether the teams can configure their categories
                      themselves, defaults to True
        hidden: If True, teams will not see their categories.
                `hidden == True` implies `configurable == False`.
        scoreboard: Scoreboard enum.
    """

    def __init__(
        self,
        lang_to_categories={},
        configurable=True,
        hidden=False,
        scoreboard=Scoreboard.ALL,
    ):
        if not isinstance(lang_to_categories, dict) or not all(
            isinstance(lang, basestring)
            and isinstance(categories, dict)
            and all(
                isinstance(id, int) and isinstance(name, basestring)
                for id, name in categories.items()
            )
            for lang, categories in lang_to_categories.items()
        ):
            raise TypeError(lang_to_categories)
        if not isinstance(configurable, bool):
            raise TypeError(configurable)
        if not isinstance(hidden, bool):
            raise TypeError(hidden)
        if not isinstance(scoreboard, Scoreboard):
            raise TypeError(scoreboard)
        if scoreboard not in _SCOREBOARD.values():
            raise ValueError(scoreboard)

        def sort(categories):
            choices = [(id, name) for id, name in categories.items()]
            choices.sort(key=lambda f: f[0])
            return OrderedDict(choices)

        self.lang_to_categories = {
            lang: sort(categories) for lang, categories in lang_to_categories.items()
        }
        self.configurable = configurable and not hidden
        self.hidden = hidden
        self.scoreboard = scoreboard

    def is_configurable_and_nonempty(self):
        """Returns True if the teams are allowed to configure the category
        themselves and if there are any categories at all."""
        return self.configurable and any(
            len(categories) > 0 for categories in self.lang_to_categories.values()
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
    KIND = dict(KIND_CHOICES)

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
    url_path_prefix = models.CharField(
        blank=True,
        max_length=64,
        help_text="The URL with a leading and a trailing slash, e.g. /somename/",
    )
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
        "The category 0 is the default. "
        "Thus, it is recommended to always define the category 0. "
        "Optionally, add a '\"CONFIGURABLE\": false' element to denote that "
        "teams cannot themselves modify the category. "
        "Add '\"HIDDEN\": true' to hide team categories from non-admins. "
        "Set \"SCOREBOARD\" to \"ALL_AND_NONZERO_EACH\" to show separate scoreboards per non-zero categories, "
        "to \"ALL_AND_NONZERO_MY\" to show only the scoreboard of the active team if its category is non-zero, "
        "to \"ALL_AND_NONZERO_MY_THEN_REST\" to show separate but with active team's category on top, "
        "or to \"ALL\" to only show one scoreboard. "
        "Note: team categories will be visible even if \"HIDDEN\" is false!",
    )
    # TODO: Remove this field.
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
        if self.url_path_prefix:
            return self.url_path_prefix
        elif self.is_course:
            return '/course/{}/'.format(self.id)
        else:
            return '/competition/{}/'.format(self.id)

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
            u'<a href="{}">{}</a>'.format(self.get_scoreboard_url(), xss.escape(title))
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

    def parse_team_categories(self):
        """
        Parse the `team_categories` field and return a TeamCategories.

        Format (JSON):
            {
                "lang1": {"ID1": "name", ...},
                ...,
                "CONFIGURABLE": true/false,
                "HIDDEN": true/false
                "SCOREBOARD": true/false,
            }'
        Old format (deprecated):
            "ID1: name | ..."

        The "CONFIGURABLE" key is optional and defaults to True.
        The "HIDDEN" key is optional and defaults to False.
        Note: HIDDEN == False impliest CONFIGURABLE == False.

        Returns None if the format is invalid."""

        # TODO: The function should return a human readable message in case of
        # a format error.
        def inner():
            if not self.team_categories.strip():
                return TeamCategories(lang_to_categories={}, configurable=False)
            if not self.team_categories.startswith('{'):
                return self._parse_team_categories_old(self.team_categories)

            parsed = json.loads(self.team_categories)
            configurable = bool(parsed.pop("CONFIGURABLE", True))
            hidden = bool(parsed.pop("HIDDEN", False))
            scoreboard = _SCOREBOARD[parsed.pop("SCOREBOARD", "ALL")]
            lang_to_categories = {
                lang: {int(id): key for id, key in categories.items()}
                for lang, categories in parsed.items()
            }
            return TeamCategories(lang_to_categories, configurable, hidden, scoreboard)

        try:
            return inner()
        except Exception:
            return None

    @staticmethod
    def _parse_team_categories_old(team_categories):
        # TODO: Remove.

        # Format is "ID1:name1 | ID2:name2 | ...", where the last item is
        # considered the default.
        categories = {}
        for category in team_categories.split('|'):
            if not category.strip():
                continue
            category = category.split(':')
            if len(category) != 2:
                raise ValueError("Invalid format of team_categories!")
            ID = int(category[0])  # Might raise a ValueError.
            name = category[1].strip()
            categories[ID] = name

        lang_to_categories = {
            lang: categories for lang, lang_name in settings.LANGUAGES
        }
        return TeamCategories(lang_to_categories, configurable=True)

    @property
    def are_teams_editable(self):
        """Teams are editable if at least one of the following holds:
        - the competition is a team competition,
        - teams can configure team categories, i.e. team_categories does not
          contain a `"CONFIGURABLE": false` item.
        """
        if self.max_team_size > 1:
            return True

        try:
            return self.parse_team_categories().is_configurable_and_nonempty()
        except:  # noqa: E722 do not use bare 'except'
            return False

    @property
    def are_team_names_configurable(self):
        return self.max_team_size > 1

    @property
    def is_course(self):
        return self.kind == self.KIND_COURSE

    @property
    def is_individual_competition(self):
        return self.max_team_size == 1

    @property
    def is_team_competition(self):
        return self.max_team_size > 1

    @property
    def use_days_for_chain_time(self):
        """Return whether unlock and close time should be displayed and entered
        in days instead of minutes."""
        return (
            self.end_date - self.start_date
            >= settings.USE_DAYS_FOR_CHAIN_TIME_THRESHOLD
        )

    def is_user_admin(self, user):
        return self.user_has_perm(user, EDIT)

    def get_rules_page_name(self):
        """For competitions use "rules", but for courses use "instructions"."""
        if self.is_course:
            return _("Course Instructions")
        else:
            return _("Competition Rules")

    def get_rules_terminology(self):
        if self.is_course:
            return RulesTerminology.INSTRUCTIONS
        else:
            return RulesTerminology.RULES

    def get_rules_url(self):
        """Return the URL for either the rules (for competitions) or the
        instructions (for courses)."""
        if self.is_course:
            return join_urls(self.get_absolute_url(), 'instructions')
        else:
            return join_urls(self.get_absolute_url(), 'rules')

    def get_team_metaname(self):
        """Return "Team", "Competitor" or "Participant", depending on whether this
        is a team competition or not, and whether it is a competition or a course."""
        # TODO: We should probably take into account the gender, if specified.
        if self.is_team_competition:
            return _("Team")
        elif self.is_course:
            return _("Participant")
        else:
            return _("Competitor")

    def get_team_metaname_plural(self):
        """Return "Teams", "Competitors" or "Participants", depending on whether this
        is a team competition or not, and whether it is a competition or a course."""
        if self.is_team_competition:
            return _("Teams")
        elif self.is_course:
            return _("Participants")
        else:
            return _("Competitors")

    def get_team_metaname_plural_all(self):
        """Return "All teams", "All competitors" or "All participants",
        depending on whether this is a team competition or not, and whether it
        is a competition or a course."""
        if self.is_team_competition:
            return _("All teams")
        elif self.is_course:
            return _("All participants")
        else:
            return _("All competitors")

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
    UNLOCK_MODES = {
        UNLOCK_GRADUAL: ugettext_lazy("Gradual unlocking"),
        UNLOCK_ALL: ugettext_lazy("All tasks unlocked"),
    }

    competition = models.ForeignKey(Competition)
    name = models.CharField(max_length=200)
    unlock_minutes = models.IntegerField(
        default=0,
        help_text=ugettext_lazy(
            # Note: this text should work for unlock_days as well.
            "The time after the beginning of the competition/course, "
            "after which the chain becomes visible to participants."
        ),
    )

    # Note: "close_minutes" and "unlock_minutes" do not have a fully symmetric
    # meaning, hence the different name. "Unlock" means that the chain is going
    # to become visible, whereas "close" means that no submissions will be
    # possible but that the chain will still be visible.
    close_minutes = models.IntegerField(
        default=0,
        help_text=ugettext_lazy(
            # Note: this text should work for close_days as well.
            "The time after the beginning of the competition/course, "
            "after which tasks of the chain are closed for submissions. "
            "Note: all tasks of the chain will become visible after closing the chain! "
            "Set to 0 to disable. "
        ),
    )

    # Category is currently a string which stores the category name (title),
    # translations and ordering. See views/utils_chain.py for more info.
    # Categories are considered equal if the strings match exactly. In the
    # future, we may consider adding a new model Category. So far this suffices.
    category = models.CharField(blank=True, db_index=True, max_length=200)
    position = models.IntegerField(
        default=0,
        help_text=ugettext_lazy("Position in the category."),
    )
    bonus_score = models.IntegerField(
        default=1,
        help_text=ugettext_lazy(
            "Additional points awarded for fully solving all tasks of the chain."
        ),
    )
    unlock_mode = models.SmallIntegerField(
        choices=list(UNLOCK_MODES.items()),
        default=UNLOCK_GRADUAL,
        help_text=ugettext_lazy(
            "Either gradual unlocking (tasks unlocked one by one as they are solved "
            "or as all attempts are used up), or all tasks unlocked simultaneously."
        ),
    )

    # The restricted access is not called "hidden", as done elsewhere, because
    # in this case we do not rely on ObjectPermission (which is Group-based),
    # but on a custom ChainTeam many-to-many field.
    restricted_access = models.BooleanField(
        default=False,
        help_text=ugettext_lazy(
            "If enabled, only teams with explicitly given access will be able to view and solve this chain."
        ),
    )
    teams_with_access = models.ManyToManyField(
        Team, related_name='explicitly_accessible_chains', through='ChainTeam'
    )

    cache_ctask_comments_info = models.CharField(blank=True, max_length=255)
    cache_is_verified = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return self.competition.get_absolute_url() + 'chain/{}/'.format(self.id)

    def team_has_access(self, team):
        if self.restricted_access:
            if team:
                return ChainTeam.objects.filter(chain=self, team=team).exists()
            else:
                return False
        else:
            return True

    def is_closed(self, minutes_passed):
        """Given the current relative competition time in minutes, return whether
        the chain is already closed, with respect to the `close_minutes` field."""
        return self.close_minutes > 0 and minutes_passed >= self.close_minutes

    @property
    def unlock_days(self):
        return self.unlock_minutes / (24 * 60.0)

    @property
    def close_days(self):
        return self.close_minutes / (24 * 60.0)


class ChainTeam(models.Model):
    """Explicit Team-Chain permissions."""

    chain = models.ForeignKey(Chain, db_index=True)
    team = models.ForeignKey(Team, db_index=True)

    class Meta:
        unique_together = (('chain', 'team'),)


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
