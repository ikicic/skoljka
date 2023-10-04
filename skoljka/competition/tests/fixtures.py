import datetime
import json

from django.contrib.auth.models import Group, User
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from skoljka.competition.models import Chain, Competition, CompetitionTask
from skoljka.competition.utils import create_ctask
from skoljka.mathcontent.models import MathContent
from skoljka.permissions.constants import EDIT, VIEW
from skoljka.permissions.models import ObjectPermission
from skoljka.usergroup.models import UserGroup
from skoljka.usergroup.utils import add_users_to_group
from skoljka.userprofile.models import create_user_profile
from skoljka.utils.testutils import assert_testdb

TEST_COMPETITION_URLS = {
    10001: 'empty_competition',
}

TEST_USER_PASSWORD = 'a'


def create_empty_competition(moderators):
    """Create an active hidden competition."""
    HOUR = datetime.timedelta(hours=1)
    NOW = datetime.datetime.now()

    # TODO: Use some kind of API for creating a group.
    group = Group.objects.create(name="empty_competition_group")
    group_description = MathContent.objects.create(text="abcdef")
    UserGroup.objects.create(
        group=group, description=group_description, author=moderators[0]
    )
    add_users_to_group(moderators, group, added_by=None)

    competition = Competition.objects.create(
        id=10001,
        name="Empty test competition",
        hidden=True,
        kind=Competition.KIND_COMPETITION,
        admin_group_id=group.id,
        registration_open_date=NOW - 24 * HOUR,
        start_date=NOW - 1 * HOUR,
        scoreboard_freeze_date=NOW - 23 * HOUR,
        end_date=NOW + 24 * HOUR,
        url_path_prefix='/empty_competition/',
    )

    ObjectPermission.objects.create(
        content_object=competition, group=group, permission_type=EDIT
    )
    ObjectPermission.objects.create(
        content_object=competition, group=group, permission_type=VIEW
    )

    return competition


def create_n_users(prefix, n):
    """Create `n` users, with username `prefix + str(i)`, where `i` goes from
    `0` to `n-1`."""
    users = []
    for i in range(n):
        user = User.objects.create(
            username="{}{}".format(prefix, i),
            is_active=True,
            is_superuser=False,
            is_staff=False,
        )
        user.set_password(TEST_USER_PASSWORD)
        user.save()
        create_user_profile(user)
        users.append(user)

    return users


@csrf_exempt
@assert_testdb
def create_test_competitions(request):
    """Fill the database will all default data for testing competitions."""
    moderators = create_n_users("moderator", 5)
    create_n_users("competitor", 10)
    create_empty_competition(moderators)
    response = {}
    return HttpResponse(json.dumps(response), mimetype='application/json')


def _create_test_ctasks(request, competition_id, chain=None):
    if not request.user.is_authenticated():
        return HttpResponseBadRequest("must be signed in as the ctask author")

    competition = Competition.objects.get(id=competition_id)
    num_tasks = int(request.POST['num-tasks'])
    text_format = request.POST['text-format']
    comment_format = request.POST['comment-format']

    ctask_ids = []
    for i in range(num_tasks):
        # Note: chain_position is for some reason assumed to be 1-based.
        ctask = CompetitionTask(
            competition=competition,
            descriptor=str(100 + i),
            max_submissions=competition.default_max_submissions,
            chain=chain,
            chain_position=(-1 if chain is None else i + 1),
        )
        create_ctask(
            ctask,
            request.user,
            competition,
            text_format.format(i),
            comment_format.format(i),
        )
        ctask_ids.append(ctask.id)

    return ctask_ids


@csrf_exempt
@assert_testdb
def create_test_ctasks(request, competition_id):
    """Create multiple ctasks.

    POST arguments:
        num-tasks: number of ctasks to create
        text-format: .format()-compatible format for the ctask text
        comment-format: .format()-compatible format for the ctask comment

    Returns a JSON:
        {'ctask_ids': [...]}
    """
    ctask_ids = _create_test_ctasks(request, competition_id)
    response = {'ctask_ids': ctask_ids}
    return HttpResponse(json.dumps(response), mimetype='application/json')


@csrf_exempt
@assert_testdb
def create_test_chain(request, competition_id):
    """Create multiple ctasks.

    Chain POST arguments:
        name
        unlock-minutes
        category
        bonus
        position
        unlock-mode

    Ctask POST arguments:
        num-tasks: number of ctasks to create and assign to the chain
        text-format: .format()-compatible format for the ctask text
        comment-format: .format()-compatible format for the ctask comment

    Returns a JSON:
        {'chain_id': chain.id, 'ctask_ids': [...]}
    """
    competition = Competition.objects.get(id=competition_id)
    chain = Chain.objects.create(
        competition=competition,
        name=request.POST['name'],
        unlock_minutes=request.POST['unlock-minutes'],
        category=request.POST['category'],
        bonus_score=request.POST['bonus'],
        position=request.POST['position'],
        unlock_mode=request.POST['unlock-mode'],
    )
    ctask_ids = _create_test_ctasks(request, competition_id, chain=chain)
    response = {'chain_id': chain.id, 'ctask_ids': ctask_ids}
    return HttpResponse(json.dumps(response), mimetype='application/json')
