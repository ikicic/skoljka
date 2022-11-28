import os
import sys
import tempfile

from django.conf import settings

from skoljka.task.tests.utils import create_task
from skoljka.userprofile.tests.utils import TestCaseWithUsersAndFolders
from skoljka.utils.testcase import TemporaryMediaRootMixin

from skoljka.mathcontent.models import Attachment, LatexElement, MathContent

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

    def test_attachments(self):
        task1 = create_task(self.user1, "task 1", "some text 1")
        task1b = create_task(self.user1, "task 1 2", "some text 1 2")
        task2 = create_task(self.user2, "task 2", "some text 2")

        with tempfile.NamedTemporaryFile() as f:
            f.write("some file content")
            f.flush()

            # user1 should not be able to add attachments to user2's tasks.
            f.seek(0)
            self.login(self.user1)
            response = self.client.post(
                    task2.content.get_edit_attachments_url(),
                    {'file': f})
            self.assertResponse(response, 404)

            # The server should not crash on bad requests (of user1).
            response = self.client.post(task1.content.get_edit_attachments_url(), {})
            self.assertResponse(response, 200)
            self.assertEqual(Attachment.objects.count(), 0)

            # user1 should be able to add attachments to their own task.
            f.seek(0)
            self.login(self.user1)
            response = self.client.post(
                    task1.content.get_edit_attachments_url(),
                    {'file': f})
            self.assertRedirects(response, task1.content.get_edit_attachments_url())
            attachments = list(Attachment.objects.all())
            self.assertEqual(len(attachments), 1)
            attachment = attachments[0]
            self.assertEqual(attachment.content, task1.content)
            self.assertGreater(attachment.cache_file_size, 0)

            # The file name should be preserved.
            filename = os.path.basename(f.name)
            self.assertEqual(os.path.basename(attachment.file.name), filename)
            self.assertTrue(attachment.get_url().endswith(filename))

        # The file should actually be accessible.
        self.assertResponse(
                self.client.get(attachment.get_url()),
                200, "some file content")

        # user2 should not be able to delete user1's attachment.
        self.login(self.user2)
        response = self.client.post(
                attachment.content.get_edit_attachments_url(),
                {'delete_attachment_id': attachment.id})
        self.assertResponse(response, 404)

        # user2 should not be able to delete user1's attachment by manipulating URL and POST.
        response = self.client.post(
                task2.content.get_edit_attachments_url(),
                {'delete_attachment_id': attachment.id})
        self.assertResponse(response, 403)
        self.assertEqual(Attachment.objects.count(), 1)

        # user1 should not be able to delete their own attachment by manipulating URL and POST.
        self.login(self.user1)
        response = self.client.post(
                task1b.content.get_edit_attachments_url(),
                {'delete_attachment_id': attachment.id})
        self.assertResponse(response, 403)

        # user1 should be able to delete their attachment.
        content = attachment.content
        path = attachment.file.name
        url = attachment.get_url()
        response = self.client.post(
                attachment.content.get_edit_attachments_url(),
                {'delete_attachment_id': attachment.id})
        self.assertRedirects(response, content.get_edit_attachments_url())

        # The attachment should not exist anymore.
        self.assertEqual(Attachment.objects.count(), 0)
        self.assertResponse(self.client.get(url), 404)
        with self.assertRaises(IOError):
            with open(path):
                pass
        # TODO: Remove in Python 3. For some reason, in Python 2,
        #       sys.exc_info() contains the old exception.
        sys.exc_clear()

        # Clean up, the context manager will check if the folder is empty.
        os.rmdir(os.path.join(settings.MEDIA_ROOT, 'attachment', '0'))
        os.rmdir(os.path.join(settings.MEDIA_ROOT, 'attachment'))
