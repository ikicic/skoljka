from tags.utils import add_task_tags, get_available_tags, \
        get_object_tagged_items, split_tag_ids, split_tags, \
        replace_with_original_tags
from tags.tests.test_base import TagsTestCaseBase


class TagsUtilsTestCase(TagsTestCaseBase):
    def test_split_tags(self):
        CHECK = lambda x, y, z = "": \
                self.assertEqual(sorted(split_tags(x)), sorted(y), z)
        CHECK("first, second, third", ["first", "second", "third"])
        CHECK("First, seCOND, THIRD", ["First", "seCOND", "THIRD"],
                "should keep cases")
        CHECK("two words", ["two words"], "should support multiple word tags")
        CHECK("two   words", ["two words"], "should remove extra spaces")
        CHECK("one, one two, one two three", ["one", "one two", "one two three"])
        CHECK("a,b,c,b", ["a", "b", "c"], "should remove duplicated")
        CHECK("b,,a,,,,c,,d", ["a", "b", "c", "d"], "should remove empty tags")
        CHECK(["already", "split"], ["already", "split"])
        CHECK(None, [], "should accept None as empty list")
        with self.assertRaises(ValueError): split_tags({"a": 124})
        with self.assertRaises(ValueError): split_tags(12312313)

    def test_split_tag_ids(self):
        CHECK = lambda x, y, z = None: self.assertEqual(split_tag_ids(x), y, z)
        CHECK("123", [123])
        CHECK("10,20,30,40,50,15", [10, 20, 30, 40, 50, 15])
        CHECK("50, 40, 30, 25", [50, 40, 30, 25])
        CHECK([20, 10, 30], [20, 10, 30], "should accept lists")

    def test_get_available_tags(self):
        def CHECK(x, y, z = None):
            result = get_available_tags(x).values_list('name', flat=True)
            self.assertEqual(sorted(result), sorted(y), z)
        CHECK("IMO, alg, geo", ["IMO", "alg", "geo"], "should work with strings")
        CHECK(["IMO", "alg", "geo"], ["IMO", "alg", "geo"], "should work with lists")
        CHECK("IMO, alg, nonexistent, tb", ["IMO", "alg", "tb"], "should ignore nonexistent tags")
        CHECK("imo, mEMo", ["IMO", "MEMO"], "should be case insensitive")

    def test_replace_with_original_tags(self):
        CHECK = lambda x, y, z = None: \
                self.assertEqual(
                        sorted(replace_with_original_tags(x)), sorted(y), z)
        CHECK("imo,memo", ["IMO", "MEMO"], "should fix cases")
        CHECK("wEiRD", ["wEiRD"], "should keep cases for unknown tags")
        CHECK("geo,imo,2007,NEWTAG", ["geo", "IMO", "2007", "NEWTAG"])
        CHECK(["Imo", "asdf"], ["IMO", "asdf"], "should work with lists")

    def test_add_task_tags(self):
        CHECK = lambda x, y, z = None: \
            self.assertEqual(
                    sorted(x.tags.values_list('name', flat=True)), sorted(y), z)
        self._set_up_tasks()

        # TODO: check signals
        CHECK(self.task1, ["MEMO", "alg"])
        add_task_tags("memo, tb", self.task1)
        CHECK(self.task1, ["MEMO", "alg", "tb"])
        CHECK(self.task2, ["IMO", "geo"])
        add_task_tags("asdf, asdf2", self.task2)
        CHECK(self.task2, ["IMO", "geo", "asdf", "asdf2"])

        self.task1._cache_tagged_items = -1
        add_task_tags("memo", self.task1)
        self.assertIsNotNone(self.task1._cache_tagged_items,
                "shouldn't clear ._cache_tagged_items if no new tags added")
        add_task_tags("new-tag", self.task1)
        self.assertFalse(hasattr(self.task1, '._cache_tagged_items'),
                "should delete ._cache_tagged_items if new tags added")

    def test_get_object_tagged_items(self):
        def CHECK(x, y, z = None):
            names = [item.tag.name for item in get_object_tagged_items(x)]
            self.assertEqual(sorted(names), sorted(y), z)

        self._set_up_tasks()
        CHECK(self.task1, ["MEMO", "alg"])
        self.assertIsNotNone(self.task1._cache_tagged_items,
                "should fill ._cache_tagged_items")

        CHECK(self.task2, ["IMO", "geo"])
        add_task_tags("tb, asdf", self.task2)
        CHECK(self.task2, ["IMO", "geo", "tb", "asdf"])
