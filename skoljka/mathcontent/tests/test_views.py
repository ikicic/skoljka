import os

from django.conf import settings

from skoljka.userprofile.tests.utils import TestCaseWithUsersAndFolders
from skoljka.utils.testcase import TemporaryMediaRootMixin

from skoljka.mathcontent.models import LatexElement

class MathContentViewsTest(TemporaryMediaRootMixin,
                           TestCaseWithUsersAndFolders):
    def get_preview(self, text):
        response = self.client.get(
                '/ajax/mathcontent/preview/',
                {'text': text},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        return response

    def test_ajax_preview(self):
        # Non-authenticated users cannot use preview.
        self.assertResponse(self.get_preview("$x + y$"), 403)

        # Check preview with no LaTeX.
        self.login(self.user1)
        self.assertResponse(self.get_preview("Hello!"),
                            200, '<p class="mc-noindent">Hello!')

        # Check preview with LaTeX.
        response = self.get_preview("$x + y$")
        elements = list(LatexElement.objects.all())
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].text, "x + y")
        self.assertEqual(elements[0].format, '$%s$')

        h = elements[0].hash
        img = '<img src="/media/m/{}/{}/{}/{}.png" alt="x + y" '\
              'class="latex" style="vertical-align:{}px">'.format(
                      h[0], h[1], h[2], h, -elements[0].depth)
        self.assertResponse(response, 200, '<p class="mc-noindent">' + img)

        # Clean-up.
        os.remove(os.path.join(settings.MEDIA_ROOT, 'm', h[0], h[1], h[2], h + '.png'))
        os.rmdir(os.path.join(settings.MEDIA_ROOT, 'm', h[0], h[1], h[2]))
        os.rmdir(os.path.join(settings.MEDIA_ROOT, 'm', h[0], h[1]))
        os.rmdir(os.path.join(settings.MEDIA_ROOT, 'm', h[0]))
        os.rmdir(os.path.join(settings.MEDIA_ROOT, 'm'))
