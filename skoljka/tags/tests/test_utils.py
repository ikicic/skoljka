from django.test import TestCase

from skoljka.tags.models import Tag
from skoljka.tags.tests.test_base import TagsTestCaseBase
from skoljka.tags.utils import (
    add_tags,
    get_available_tags,
    get_object_tagged_items,
    replace_with_original_tags,
    split_tag_ids,
    split_tags,
    tag_names_to_ids,
)


class TagsUtilsTestCase(TagsTestCaseBase):
    def test_split_tags(self):
        CHECK = lambda x, y, z="": self.assertEqual(sorted(split_tags(x)), sorted(y), z)
        CHECK("first, second, third", ["first", "second", "third"])
        CHECK("First, seCOND, THIRD", ["First", "seCOND", "THIRD"], "should keep cases")
        CHECK("two words", ["two words"], "should support multiple word tags")
        CHECK("two   words", ["two words"], "should remove extra spaces")
        CHECK("one, one two, one two three", ["one", "one two", "one two three"])
        CHECK("a,b,c,b", ["a", "b", "c"], "should remove duplicated")
        CHECK("b,,a,,,,c,,d", ["a", "b", "c", "d"], "should remove empty tags")
        CHECK(["already", "split"], ["already", "split"])
        CHECK(None, [], "should accept None as empty list")
        with self.assertRaises(ValueError):
            split_tags({"a": 124})
        with self.assertRaises(ValueError):
            split_tags(12312313)

    def test_split_tag_ids(self):
        CHECK = lambda x, y, z=None: self.assertEqual(split_tag_ids(x), y, z)
        CHECK("123", [123])
        CHECK("10,20,30,40,50,15", [10, 20, 30, 40, 50, 15])
        CHECK("50, 40, 30, 25", [50, 40, 30, 25])
        CHECK([20, 10, 30], [20, 10, 30], "should accept lists")

    def test_get_available_tags(self):
        def CHECK(x, y, z=None):
            result = get_available_tags(x).values_list('name', flat=True)
            self.assertEqual(sorted(result), sorted(y), z)

        CHECK("IMO, alg, geo", ["IMO", "alg", "geo"], "should work with strings")
        CHECK(["IMO", "alg", "geo"], ["IMO", "alg", "geo"], "should work with lists")
        CHECK(
            "IMO, alg, nonexistent, tb",
            ["IMO", "alg", "tb"],
            "should ignore nonexistent tags",
        )
        CHECK("imo, mEMo", ["IMO", "MEMO"], "should be case insensitive")

    def test_replace_with_original_tags(self):
        CHECK = lambda x, y, z=None: self.assertEqual(
            sorted(replace_with_original_tags(x)), sorted(y), z
        )
        CHECK("imo,memo", ["IMO", "MEMO"], "should fix cases")
        CHECK("wEiRD", ["wEiRD"], "should keep cases for unknown tags")
        CHECK("geo,imo,2007,NEWTAG", ["geo", "IMO", "2007", "NEWTAG"])
        CHECK(["Imo", "asdf"], ["IMO", "asdf"], "should work with lists")

    def test_add_tags(self):
        CHECK = lambda x, y, z=None: self.assertEqual(
            sorted(x.tags.values_list('name', flat=True)), sorted(y), z
        )
        self._set_up_tasks()

        CHECK(self.alice_task, ["MEMO", "alg"])
        add_tags(self.alice_task, "memo, tb")
        CHECK(self.alice_task, ["MEMO", "alg", "tb"])
        CHECK(self.admin_task, ["IMO", "geo"])
        add_tags(self.admin_task, "asdf, asdf2")
        CHECK(self.admin_task, ["IMO", "geo", "asdf", "asdf2"])

        self.alice_task._cache_tagged_items = -1
        add_tags(self.alice_task, "memo")
        self.assertIsNotNone(
            self.alice_task._cache_tagged_items,
            "shouldn't clear ._cache_tagged_items if no new tags added",
        )
        add_tags(self.alice_task, "new-tag")
        self.assertFalse(
            hasattr(self.alice_task, '._cache_tagged_items'),
            "should delete ._cache_tagged_items if new tags added",
        )

    def test_get_object_tagged_items(self):
        def CHECK(x, y, z=None):
            names = [item.tag.name for item in get_object_tagged_items(x)]
            self.assertEqual(sorted(names), sorted(y), z)

        self._set_up_tasks()
        CHECK(self.alice_task, ["MEMO", "alg"])
        self.assertIsNotNone(
            self.alice_task._cache_tagged_items, "should fill ._cache_tagged_items"
        )

        CHECK(self.admin_task, ["IMO", "geo"])
        add_tags(self.admin_task, "tb, asdf")
        CHECK(self.admin_task, ["IMO", "geo", "tb", "asdf"])


class TestTagNamesToIds(TestCase):
    def test_add_false(self):
        Tag.objects.create(name="one")
        Tag.objects.create(name="two")
        Tag.objects.create(name="three")
        Tag.objects.create(name="four")
        self.assertItemsEqual(tag_names_to_ids("one,two,three"), [1, 2, 3])
        self.assertItemsEqual(tag_names_to_ids("ONe,TwO,three"), [1, 2, 3])
        self.assertItemsEqual(tag_names_to_ids(["three", "two", "one"]), [1, 2, 3])
        self.assertItemsEqual(tag_names_to_ids("three,two,one,foo"), [1, 2, 3])
        self.assertItemsEqual(tag_names_to_ids("one,four"), [1, 4])
        self.assertItemsEqual(tag_names_to_ids(""), [])
        self.assertItemsEqual(tag_names_to_ids("foo,bar"), [])
        self.assertEqual(Tag.objects.all().count(), 4)

    def test_add_true(self):
        Tag.objects.create(name="one")
        Tag.objects.create(name="two")
        Tag.objects.create(name="three")
        self.assertItemsEqual(tag_names_to_ids("one,two,three", add=True), [3, 2, 1])
        self.assertEqual(Tag.objects.all().count(), 3)
        self.assertItemsEqual(tag_names_to_ids("one,four", add=True), [1, 4])
        self.assertEqual(Tag.objects.all().count(), 4)
        self.assertItemsEqual(tag_names_to_ids("FOO,BaR", add=True), [5, 6])
        self.assertEqual(Tag.objects.all().count(), 6)

        new_tags = Tag.objects.filter(id__in=[5, 6]).values_list('name', flat=True)
        self.assertItemsEqual(new_tags, ["FOO", "BaR"])
