from random import SystemRandom

from django.conf import settings

from skoljka.mathcontent.latex import get_or_generate_png
from skoljka.utils.testutils import IS_TESTDB


class InvalidChallengeKey(Exception):
    pass


class Challenge(object):
    def __init__(self, index):
        self.index = index


class ChallengeHandler(object):
    """Generates, encrypts and decrypts challenges."""

    def __init__(self, challenges):
        """
        Arguments:
            challenges: A list of (challenge, answer) pairs of strings.
        """
        self.challenges = challenges
        self._latex_cache = [None] * len(challenges)

    def create_random(self):
        """Create a random Challenge object."""
        index = SystemRandom().randrange(len(self.challenges))
        return Challenge(index)

    @staticmethod
    def get_or_generate_png(format, content):
        """Used to mock the get_or_generate_png from mathcontent."""
        return get_or_generate_png(format, content)

    def to_key(self, challenge):
        """Return an identifier of the current challenge."""
        return str(challenge.index)

    def from_key(self, key):
        """Return a Challenge, given a parsed challenge. Returns None if parsing fails."""
        try:
            index = int(key)
        except:  # noqa: E722
            raise InvalidChallengeKey("key not a number")

        if index >= len(self.challenges):
            raise InvalidChallengeKey(
                "key index {} out of range {}".format(index, len(self.challenges))
            )

        return Challenge(index)

    def to_html(self, challenge):
        """Generate or load the PNG of the challenge and return it as an <img>
        string. The tag contains no alt="..." tag."""
        cache = self._latex_cache[challenge.index]
        if cache:
            return cache
        expression, _ = self.challenges[challenge.index]
        latex_element = self.get_or_generate_png('$%s$', expression)
        html = u'<img src="{}" class="latex" style="vertical-align:{}px">'.format(
            latex_element.get_url(), -latex_element.depth
        )
        self._latex_cache[challenge.index] = html
        return html

    def is_answer_correct(self, challenge, answer):
        """Returns True if the answer matches the expected one, or False otherwise."""
        _, expected_answer = self.challenges[challenge.index]
        return answer == expected_answer


class TestChallengeHandler(ChallengeHandler):
    """ChallengeHandler with challenges
    0: 0 + sqrt(400) == 20
    1: 10 + sqrt(400) == 30
    2: 20 + sqrt(400) == 40
    ...
    9: 90 + sqrt(400) == 110
    """

    def __init__(self, challenges=None):
        if challenges is None:
            challenges = [
                (r'{} + \sqrt{{400}} = '.format(10 * i), str(10 * i + 20))
                for i in range(10)
            ]
        super(TestChallengeHandler, self).__init__(challenges)


challenge_handler = ChallengeHandler(settings.REGISTRATION_CHALLENGES)

if IS_TESTDB:
    test_challenge_handler = TestChallengeHandler()
