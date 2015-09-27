from django.contrib.contenttypes.models import ContentType
from tags.tests.test_base import TagsTestCaseBase


class TagsAJAXTestCase(TagsTestCaseBase):
    def _post(self, obj, url, post):
        post['object_id'] = obj.id
        post['content_type_id'] = ContentType.objects.get_for_model(obj).id
        return self.client.post(
                url, post, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def _post_add(self, obj, post):
        return self._post(obj, '/ajax/tag/add/', post)

    def _post_delete(self, obj, post):
        return self._post(obj, '/ajax/tag/delete/', post)

    def test_add(self):
        self._set_up_tasks()
        # TODO: Login from the base userprofile test class, once it's made.
        self.client.login(username=self.alice.username, password='a')

        # Empty name
        response = self._post_add(self.alice_task, {'name': ""})
        self.assertContains(response, "at least one character long", 
                status_code=400)

        # Add tag with known name
        self.assertTagsEqual(self.alice_task, ["alg", "MEMO"])
        response = self._post_add(self.alice_task, {'name': "tb"})
        self.assertTagsEqual(self.alice_task, ["alg", "MEMO", "tb"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1')

        # Add tag with unknown name
        response = self._post_add(self.alice_task, {'name': "asdf"})
        self.assertTagsEqual(self.alice_task, ["alg", "MEMO", "tb", "asdf"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1')

        # Try to add a duplicate
        response = self._post_add(self.alice_task, {'name': "asdf"})
        self.assertTagsEqual(self.alice_task, ["alg", "MEMO", "tb", "asdf"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '-1')

        # Check permissions
        response = self._post_add(self.admin_task, {'name': "asdf"})
        self.assertTagsEqual(self.admin_task, ["IMO", "geo"])
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, '0')

    def test_add_disallowed_tags_admin(self):
        self._set_up_tasks()
        self.client.login(username=self.admin.username, password='a')

        response = self._post_add(self.admin_task, {'name': "news"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1')
        response = self._post_add(self.admin_task, {'name': "oldnews"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1')

    def test_add_disallowed_tags_nonadmin(self):
        self._set_up_tasks()
        self.client.login(username=self.alice.username, password='a')

        response = self._post_add(self.alice_task, {'name': "news"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '00')
        response = self._post_add(self.alice_task, {'name': "oldnews"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '00')

    def test_delete(self):
        self._set_up_tasks()
        self.client.login(username=self.alice.username, password='a')

        # Normal use case
        self.assertTagsEqual(self.alice_task, ["alg", "MEMO"])
        response = self._post_delete(self.alice_task, {'name': 'MEMO'})
        self.assertTagsEqual(self.alice_task, ["alg"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1', "should be able to delete tag")

        # Ignore unknown tags.
        response = self._post_delete(self.alice_task, {'name': 'unknown-tag'})
        self.assertTagsEqual(self.alice_task, ["alg"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1',
                "shouldn't complain if task not tagged with the tag")

        # Ignore known tags not used on this object.
        response = self._post_delete(self.alice_task, {'name': 'MEMO'})
        self.assertTagsEqual(self.alice_task, ["alg"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1',
                "shouldn't complain if task not tagged with the tag")

        # Permission check
        response = self._post_delete(self.admin_task, {'name': 'IMO'})
        self.assertTagsEqual(self.admin_task, ["geo", "IMO"])
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, '0',
                "shouldn't be able to delete task's tags without permission")

        # Task not found
        self.alice_task.id = -5
        response = self._post_delete(self.alice_task, {'name': 'MEMO'})
        self.assertEqual(response.status_code, 404)
