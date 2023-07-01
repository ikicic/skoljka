from collections import defaultdict

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import connection, models, transaction
from django.db.models import Q
from django.dispatch import receiver
from django.template.loader import add_to_builtins
from registration.signals import user_registered

from skoljka.folder.models import Folder
from skoljka.solution.models import (
    SOLUTION_CORRECT_SCORE,
    SolutionDetailedStatus,
    SolutionStatus,
)
from skoljka.tags.models import Tag
from skoljka.task.models import DIFFICULTY_RATING_ATTRS, Task
from skoljka.utils.models import icon_help_text

# TODO: clean up, move utility methods to utils.py

# Take unique ID and description
USERPROFILE_SCHOOL_CLASS_CHOICES = [(0, '-------------')] + [
    x[:2] for x in settings.USERPROFILE_SCHOOL_CLASS_INFO
]


@receiver(user_registered)
def create_user_profile(sender, user, request, **kwargs):
    # one member Group for each User
    group = Group(name=user.username)
    group.save()

    # spremi profil, ostali podaci idu preko Edit Profile
    profile = UserProfile(user=user, private_group=group)
    profile.save()

    user.groups.add(group)
    user_refresh_group_cache([user.id])


def diff_to_index(diff):
    return int(diff + 0.5)


def task_difficulty_on_update(task, field_name, old_value, new_value):
    """
    If necessary, update all difficulty distribution counters for all users
    that solved given task.
    """
    # TODO: use signals!
    old = diff_to_index(old_value)
    new = diff_to_index(new_value)

    if old == new:
        return

    # Note that all users that solved this task already have distribution
    # information.

    base = (
        'UPDATE userprofile_difficultydistribution D'
        ' INNER JOIN solution_solution S ON D.user_id = S.author_id'
        ' SET D.solved_count = D.solved_count + ({{0}})'
        ' WHERE S.task_id = {0} AND D.difficulty = {{1}} AND'
        ' (S.status = {1} OR S.status = {2} AND S.correctness_avg >= {3});'.format(
            task.id,
            SolutionStatus.AS_SOLVED,
            SolutionStatus.SUBMITTED,
            SOLUTION_CORRECT_SCORE,
        )
    )

    cursor = connection.cursor()
    cursor.execute(base.format(-1, old))
    cursor.execute(base.format(1, new))
    transaction.commit_unless_managed()


class DifficultyDistribution(models.Model):
    user = models.ForeignKey(User, related_name='diff_distribution')
    difficulty = models.IntegerField(db_index=True)
    solved_count = models.IntegerField()


def user_refresh_group_cache(user_ids):
    """
    Given the list of User ids (not UserProfiles!), refresh
    cache_group_ids field.

    Does NOT send signals!
    """
    user_group_ids = defaultdict(list)

    m2m = User.groups.through.objects.filter(user_id__in=user_ids).values_list(
        'user_id', 'group_id'
    )
    for user_id, group_id in m2m:
        user_group_ids[user_id].append(group_id)

    # Maybe just use this one query?
    # http://stackoverflow.com/questions/3935695/how-do-i-concatenate-strings-from-a-subquery-into-a-single-row-in-mysql
    for user_id, group_ids in user_group_ids.iteritems():
        UserProfile.objects.filter(user_id=user_id).update(
            cache_group_ids=','.join(str(x) for x in group_ids)
        )


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')

    # data
    # Don't ask for useless private(!) information!
    GENDER_CHOICES = (
        ('', "Neizjašnjeno"),
        ('M', "Momak"),
        ('F', "Djevojka"),
    )
    gender = models.CharField(
        blank=True,
        max_length=1,
        choices=GENDER_CHOICES,
        default='',
        verbose_name="Spol",
        help_text=icon_help_text(u"Za gramatičke i pravopisne potrebe."),
    )

    # constants
    HIDDEN_TAGS_HIDE = 0
    HIDDEN_TAGS_SHOW_IF_SOLVED = 1
    HIDDEN_TAGS_SHOW_ALWAYS = 2
    HIDDEN_TAGS_CHOICES = [(0, "Ne"), (1, "Samo za riješene zadatke"), (2, "Uvijek")]

    # options
    show_hidden_tags = models.SmallIntegerField(
        default=False,
        choices=HIDDEN_TAGS_CHOICES,
        verbose_name="Prikazuj skrivene oznake",
    )
    show_unsolved_task_solutions = models.BooleanField(
        default=False, verbose_name=u"Prikazuj rješenja neriješenih zadataka"
    )
    hide_solution_min_diff = models.FloatField(
        default=0,
        verbose_name=u"Ili ako je je težina manja od",
        help_text=icon_help_text(
            u"Na ovaj način možete odabrati da vam se uvijek prikazuju rješenja "
            u"dovoljno laganih zadataka, što je pogotovo korisno ako ste "
            u"ispravljač."
        ),
    )
    school_class = models.IntegerField(
        default=0,
        choices=USERPROFILE_SCHOOL_CLASS_CHOICES,
        verbose_name="Razred",
        help_text=icon_help_text("Za odabrane zadatke na naslovnoj stranici"),
    )

    # (any better name?)
    evaluator = models.BooleanField(
        default=False,
        verbose_name=u"Ispravljač",
        help_text=icon_help_text(
            u"Kao ispravljač bit ćete obavještavani o "
            u"poslanim rješenjima drugih korisnika."
        ),
    )
    eval_sol_last_view = models.DateTimeField(auto_now_add=True)

    # automatic options
    solution_status_filter = models.CharField(max_length=32, blank=True, default='')
    task_view_type = models.SmallIntegerField(default=0)
    similar_task_view_type = models.SmallIntegerField(default=2)

    # utility
    unread_pms = models.IntegerField(default=0)
    selected_folder = models.ForeignKey(
        Folder, blank=True, null=True, on_delete=models.SET_NULL
    )  # WARNING: This SET_NULL is very important!!
    private_group = models.OneToOneField(Group)

    # cache
    solved_count = models.IntegerField(default=0)
    cache_group_ids = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        return u"UserProfile for " + self.user.username

    def get_absolute_url(self):
        return '/profile/%d/' % self.id

    def get_diff_distribution(self):
        """
        Returns distribution as a list of integers.
        If there are no solved problems, returns list of zeros.
        """
        distribution = self.user.diff_distribution.values_list(
            'solved_count', flat=True
        ).order_by('difficulty')

        return distribution or [0] * DIFFICULTY_RATING_ATTRS['range']

    def get_group_ids(self):
        if not hasattr(self, '_group_ids'):
            self._group_ids = [int(x) for x in self.cache_group_ids.split(',')]
        return self._group_ids

    def refresh_diff_distribution(self, commit=True):
        """
        Refresh solved task counter and difficulty distribution manually.
        Not really meant to be called (but callable from admin), because
        distribution should be automatically updated on any change...
        """
        tasks = (
            Task.objects.filter(
                Q(solution__detailed_status=SolutionDetailedStatus.AS_SOLVED)
                | Q(solution__detailed_status=SolutionDetailedStatus.SUBMITTED_CORRECT),
                hidden=False,
                solution__author=self.user,
            )
            .values('id', 'difficulty_rating_avg')
            .distinct()
            .order_by()
        )

        distribution = [0] * DIFFICULTY_RATING_ATTRS['range']
        for x in tasks:
            distribution[diff_to_index(x['difficulty_rating_avg'])] += 1

        # ok, this part could be done better...
        DifficultyDistribution.objects.filter(user=self.user).delete()
        DifficultyDistribution.objects.bulk_create(
            [
                DifficultyDistribution(user=self.user, difficulty=D, solved_count=C)
                for D, C in enumerate(distribution)
            ]
        )

        self.solved_count = len(tasks)
        if commit:
            self.save()

    def update_diff_distribution(self, task, delta):
        diff = diff_to_index(task.difficulty_rating_avg)
        try:
            element = self.user.diff_distribution.get(difficulty=diff)
            element.solved_count += delta
            element.save()
        except DifficultyDistribution.DoesNotExist:
            bulk = [
                DifficultyDistribution(
                    user=self.user,
                    difficulty=x,
                    solved_count=(delta if x == diff else 0),
                )
                for x in range(0, DIFFICULTY_RATING_ATTRS['range'])
            ]
            DifficultyDistribution.objects.bulk_create(bulk)

    def check_solution_obfuscation_preference(self, task_difficulty_avg):
        """
        Returns True if the user wouldn't like to see the solution of a
        task with the given difficulty rating.
        """
        if self.show_unsolved_task_solutions:
            return False
        if task_difficulty_avg == 0:
            return True  # Rating unknown, don't show.
        return self.hide_solution_min_diff <= task_difficulty_avg


# ovo navodno nije preporuceno, ali vjerujem da ce se
# dovoljno cesto koristiti da DRY nadjaca
add_to_builtins('skoljka.userprofile.templatetags.userprofile_tags')
