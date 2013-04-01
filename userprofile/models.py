from django.contrib.auth.models import User, Group
from django.db import connection, models, transaction
from django.db.models import Q
from django.dispatch import receiver
from django.template.loader import add_to_builtins
from django.utils.html import mark_safe

from registration.signals import user_registered

from tags.models import Tag

from folder.models import Folder
from task.models import Task, DIFFICULTY_RATING_ATTRS
from solution.models import STATUS, SOLUTION_CORRECT_SCORE


@receiver(user_registered)
def create_user_profile(sender, user, request, **kwargs):
    # one member Group for each User
    group = Group(name=user.username)
    group.save()

    # spremi profil, ostali podaci idu preko Edit Profile
    profile = UserProfile(user=user, private_group=group)
    profile.save()

    user.groups.add(group)

def diff_to_index(diff):
    return int(diff + 0.5)

def task_difficulty_on_update(task, field_name, old_value, new_value):
    """
        If necessary, update all difficulty distribution counters
        for all users that solved given task.
    """
    old = diff_to_index(old_value)
    new = diff_to_index(new_value)

    if old == new:
        return

    # Note that all users that solved this task already have distribution
    # information.

    base = "UPDATE userprofile_difficultydistribution D"        \
        " INNER JOIN solution_solution S ON D.user_id = S.author_id"    \
        " SET D.solved_count = D.solved_count + ({{0}})"        \
        " WHERE S.task_id = {0} AND D.difficulty = {{1}} AND"   \
        " (S.status = {1} OR S.status = {2} AND S.correctness_avg >= {3});".format(
            task.id, STATUS['as_solved'], STATUS['submitted'],
            SOLUTION_CORRECT_SCORE
        )

    cursor = connection.cursor()
    cursor.execute(base.format(-1, old))
    cursor.execute(base.format(1, new))
    transaction.commit_unless_managed()


class DifficultyDistribution(models.Model):
    user = models.ForeignKey(User, related_name='diff_distribution')
    difficulty = models.IntegerField(db_index=True)
    solved_count = models.IntegerField()

def icon_help_text(text):
    return mark_safe(
        ' <i class="icon-question-sign" title="{}"></i>'.format(text))

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')

    # data
    # Don't ask for useless private(!) information!
    GENDER_CHOICES = (
        ('', 'Neizjašnjeno'),
        ('M', 'Momak'),
        ('F', 'Djevojka'),
    )
    gender = models.CharField(blank=True, max_length=1, choices=GENDER_CHOICES,
        default='', verbose_name='Spol', help_text=icon_help_text(
            'Za gramatičke i pravopisne potrebe.'))

    # options
    show_hidden_tags = models.BooleanField(default=False,
        verbose_name='Prikazuj skrivene tagove')
    show_unsolved_task_solutions = models.BooleanField(default=False,
        verbose_name='Prikazuj rješenja neriješenih zadataka')
    hide_solution_min_diff = models.FloatField(default=0,
        verbose_name='Ili ako je je težina manja od', help_text=icon_help_text(
        'Na ovaj način možete odabrati da vam se uvijek prikazuju rješenja '
        'dovoljno laganih zadataka, što je pogotovo korisno ako ste '
        'ispravljač.'))
    show_solution_task = models.BooleanField(default=True,
        verbose_name='Prikazuj tekst zadatka uz rješenje.')

    # (any better name?)
    evaluator = models.BooleanField(default=False, verbose_name='Ispravljač',
        help_text=icon_help_text('Kao ispravljač bit ćete obavještavani o '
        'poslanim rješenjima drugih korisnika.'))

    # automatic options
    solution_status_filter = models.CharField(max_length=32, blank=True, default='')
    task_view_type = models.SmallIntegerField(default=0)
    similar_task_view_type = models.SmallIntegerField(default=2)

    # utility
    unread_pms = models.IntegerField(default=0)
    selected_folder = models.ForeignKey(Folder, blank=True, null=True)
    private_group = models.OneToOneField(Group)

    solved_count = models.IntegerField(default=0)
    # deprecated or to fix
    score = models.FloatField(default=0)

    def __unicode__(self):
        return u'UserProfile for ' + self.user.username

    def get_absolute_url(self):
        return '/profile/%d/' % self.id

    def get_diff_distribution(self):
        """
            Returns distribution as a list of integers.
            If there are no solved problems, returns list of zeros.
        """
        distribution = self.user.diff_distribution.values_list('solved_count',
            flat=True).order_by('difficulty')

        return distribution or [0] * DIFFICULTY_RATING_ATTRS['range']

    def refresh_diff_distribution(self, commit=True):
        """
            Refresh solved task difficulty distribution manually.
            Not really meant to be called (but callable from admin), because
            distribution should be automatically updated on any change...
        """
        tasks = Task.objects.filter(
            Q(solution__status=STATUS['as_solved'])
                | Q(solution__correctness_avg__gte=SOLUTION_CORRECT_SCORE)
                & Q(solution__status=STATUS['submitted']),
            hidden=False,
            solution__author=self
        ).values('id', 'difficulty_rating_avg').distinct().order_by()

        distribution = [0] * DIFFICULTY_RATING_ATTRS['range']
        for x in tasks:
            distribution[diff_to_index(x['difficulty_rating_avg'])] += 1

        # ok, this part could be done better...
        DifficultyDistribution.objects.filter(user=self.user).delete()
        DifficultyDistribution.objects.bulk_create([
            DifficultyDistribution(user=self.user, difficulty=D, solved_count=C)
            for D, C in enumerate(distribution)])

        if commit:
            self.save()

    def update_diff_distribution(self, task, delta):
        diff = diff_to_index(task.difficulty_rating_avg)
        try:
            element = self.user.diff_distribution.get(difficulty=diff)
            element.solved_count += delta
            element.save()
        except DifficultyDistribution.DoesNotExist:
            bulk = [DifficultyDistribution(user=self.user, difficulty=x,
                    solved_count=(delta if x == diff else 0))
                for x in range(0, DIFFICULTY_RATING_ATTRS['range'])]
            DifficultyDistribution.objects.bulk_create(bulk)



# ovo navodno nije preporuceno, ali vjerujem da ce se
# dovoljno cesto koristiti da DRY nadjaca
add_to_builtins('userprofile.templatetags.userprofile_tags')
