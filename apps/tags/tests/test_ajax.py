from tags.tests.test_base import TagsTestCaseBase


class TagsAJAXTestCase(TagsTestCaseBase):
    def _post_add(self, *args, **kwargs):
        return self.client.post('/ajax/tag/add/',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest', *args, **kwargs)
    def _post_delete(self, *args, **kwargs):
        return self.client.post('/ajax/tag/delete/',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest', *args, **kwargs)

    def test_add(self):
        self._set_up_tasks()
        self.client.login(username=self.task1.author.username, password='a')

        # Empty name
        response = self._post_add({'name': "", 'task': self.task1.id})
        self.assertContains(response, "at least one character long", 
                status_code=400)

        # Add tag with known name
        self.assertTagsEqual(self.task1, ["alg", "MEMO"])
        response = self._post_add({'name': "tb", 'task': self.task1.id})
        self.assertTagsEqual(self.task1, ["alg", "MEMO", "tb"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1')

        # Add tag with unknown name
        response = self._post_add({'name': "asdf", 'task': self.task1.id})
        self.assertTagsEqual(self.task1, ["alg", "MEMO", "tb", "asdf"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1')

        # Try to add a duplicate
        response = self._post_add({'name': "asdf", 'task': self.task1.id})
        self.assertTagsEqual(self.task1, ["alg", "MEMO", "tb", "asdf"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '-1')

        # Check permissions
        response = self._post_add({'name': "asdf", 'task': self.task2.id})
        self.assertTagsEqual(self.task1, ["alg", "MEMO", "tb", "asdf"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '0')

        # Disallow certain tags
        response = self._post_add({'name': "news", 'task': self.task1.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '00')
        response = self._post_add({'name': "oldnews", 'task': self.task1.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '00')

        # TODO: signals


    def test_delete(self):
        self._set_up_tasks()
        self.client.login(username=self.task1.author.username, password='a')

        # Normal use case
        self.assertTagsEqual(self.task1, ["alg", "MEMO"])
        response = self._post_delete({'name': 'MEMO', 'task': self.task1.id})
        self.assertTagsEqual(self.task1, ["alg"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1', "should be able to delete tag")

        # Task not found
        response = self._post_delete({'name': 'MEMO', 'task': -5})
        self.assertEqual(response.status_code, 404)

        # Tag not found
        response = self._post_delete({'name': 'unknown-tag', 'task': -5})
        self.assertEqual(response.status_code, 404)

        # We reject the request if the tag name is not used, but don't reject
        # if task not tagged with given tag...
        response = self._post_delete(
                {'name': 'MEMO', 'task': self.task1.id})
        self.assertTagsEqual(self.task1, ["alg"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '1',
                "shouldn't complain if task not tagged with the tag")

        # Permission check
        response = self._post_delete({'name': 'IMO', 'task': self.task2.id})
        self.assertTagsEqual(self.task2, ["geo", "IMO"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '0',
                "shouldn't be able to delete task's tags without permission")

        # TODO: signals
