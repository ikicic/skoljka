from skoljka.mathcontent.models import LatexElement
from skoljka.userprofile.challenge import ChallengeHandler, InvalidChallengeKey
from skoljka.utils.testcase import SimpleTestCase


class MockChallengeHandler(ChallengeHandler):
    def __init__(self, *args, **kwargs):
        super(MockChallengeHandler, self).__init__(*args, **kwargs)

    @staticmethod
    def get_or_generate_png(format, content):
        return LatexElement(hash='abcdef', format=format, text=content, depth=-5)


class ChallengeTest(SimpleTestCase):
    def test_to_from_key(self):
        handler = MockChallengeHandler([('1 + 1', '2')])
        challenge = handler.create_random()
        self.assertEqual(challenge.index, 0)

        key = handler.to_key(challenge)
        parsed = handler.from_key(key)
        self.assertEqual(parsed.index, challenge.index)

    def test_invalid_decryption(self):
        handler = MockChallengeHandler([('1 + 1', '2')] * 100)
        with self.assertRaises(InvalidChallengeKey):
            handler.from_key("### not a number ###")

        with self.assertRaises(InvalidChallengeKey):
            handler.from_key("100")  # Out of bounds.

        with self.assertRaises(InvalidChallengeKey):
            handler.from_key("1000")  # Out of bounds.

    def test_to_html(self):
        handler = MockChallengeHandler([('1 + 1', '2')])
        challenge = handler.create_random()

        # Test specifically that there is no 'alt'.
        self.assertEqual(
            handler.to_html(challenge),
            u'<img src="/media/m/a/b/c/abcdef.png" class="latex" style="vertical-align:5px">',
        )
