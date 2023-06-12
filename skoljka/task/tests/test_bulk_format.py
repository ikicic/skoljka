from __future__ import print_function

from textwrap import dedent

from django.contrib.auth.models import User
from django.test import TestCase

from skoljka.folder.models import Folder
from skoljka.permissions.constants import VIEW, EDIT, DELETE, MODEL_DEFAULT

from skoljka.task import bulk_format
from skoljka.task.bulk_format import parse_bulk, parse_add_perm, \
        parse_variables, split_expression

class TaskBulkFormatTestCase(TestCase):
    fixtures = ['skoljka/userprofile/fixtures/test_userprofiles.json']

    def setUp(self):
        self.admin = User.objects.get(id=1)
        self.alice = User.objects.get(id=2)
        self.alice_folder = Folder.objects.create(name="alice's folder",
                short_name="alice's folder", author=self.alice)

    def assertParseSupersetJSON(self, input, expected):
        received = parse_bulk(self.alice, dedent(input))
        if len(received) != len(expected):
            print("EXPECTED:")
            for task in expected:
                print(task)
            print("RECEIVED:")
            for task in received:
                print(task)
            self.assertEqual(len(received), len(expected))
        for exp, rec in zip(expected, received):
            for key, value in exp.items():
                self.assertIn(key, rec.json)
                self.assertEqual(value, rec.json[key])

    def assertParseEqualJSON(self, input, expected):
        received = parse_bulk(self.alice, dedent(input))
        for exp, rec in zip(expected, received):
            for key, value in exp.items():
                self.assertIn(key, rec.json)
                self.assertEqual(value, rec.json[key])

    def assertParseRaises(self, input, exception):
        self.assertRaises(exception,
                parse_bulk, self.alice, dedent(input))


    def test_internal_split_expression(self):
        self.assertEqual(split_expression(5), [(False, "5")])
        self.assertEqual(split_expression("bla bla"), [(False, "bla bla")])
        self.assertEqual(split_expression("@{foo}"), [(True, "foo")])
        self.assertEqual(split_expression("\@{foo}"), [(False, "@{foo}")])
        self.assertEqual(split_expression("abc @{foo} def @{bar} ghi jkl"), [
                (False, "abc "), (True, "foo"), (False, " def "),
                (True, "bar"), (False, " ghi jkl")
        ])
        self.assertRaises(bulk_format.ParseError,
                split_expression, "missing a brace @{foo")
        self.assertEqual(split_expression("not missing a brace \\@{foo"),
                [(False, "not missing a brace @{foo")])

    def test_internal_parse_variables(self):
        # Without dependencies.
        self.assertEqual(parse_variables(
            {"FOO": "asdf", "BAR": "qwerty"}),
            {"FOO": "asdf", "BAR": "qwerty"})

        # With dependencies.
        self.assertEqual(parse_variables(
            {"FOO": "bla@{bar}boo", "BAR": "qwerty"}),
            {"FOO": "blaqwertyboo", "BAR": "qwerty"})
        self.assertEqual(parse_variables(
            {"A": "bla@{b}boo", "B": "two @{c} variables @{d}", "C": "x@{d}y", "D": "zz"}),
            {"A": "blatwo xzzy variables zzboo", "B": "two xzzy variables zz", "C": "xzzy", "D": "zz"})

        # Case-insensitivity
        self.assertEqual(parse_variables(
            {"ASDF": "bla @{BaNana}", "BANANA": "bnna"}),
            {"ASDF": "bla bnna", "BANANA": "bnna"})

        # Errors.
        self.assertRaises(bulk_format.CyclicDependency, parse_variables, {"A": "@{A}"})
        self.assertRaises(bulk_format.CyclicDependency, parse_variables, {"A": "@{B}", "B": "@{A}"})
        self.assertRaises(bulk_format.UnknownVariable, parse_variables, {"A": "@{B}"})

    def test_internal_parse_add_perm(self):
        self.assertEqual(
                set(parse_add_perm("foo+bar VIEW+EDIT+DELETE")),
                set([(VIEW, 'foo'), (VIEW, 'bar'),
                     (EDIT, 'foo'), (EDIT, 'bar'),
                     (DELETE, 'foo'), (DELETE, 'bar')]))

        # Ignore duplicates
        self.assertEqual(
                set(parse_add_perm("foo+bar VIEW+EDIT+DELETE+VIEW")),
                set([(VIEW, 'foo'), (VIEW, 'bar'),
                     (EDIT, 'foo'), (EDIT, 'bar'),
                     (DELETE, 'foo'), (DELETE, 'bar')]))

        # Test permission group.
        self.assertEqual(
                set(parse_add_perm("foo DEFAULT")),
                set((perm, 'foo') for perm in MODEL_DEFAULT))

        # Test parameter count.
        self.assertRaises(bulk_format.InvalidParameter, parse_add_perm, "foo")
        self.assertRaises(bulk_format.InvalidParameter, parse_add_perm, "foo EDIT asdf")

        # Test unknown permissions.
        self.assertRaises(bulk_format.InvalidParameter, parse_add_perm, "foo ASDF")


    def test_simple(self):
        self.assertParseEqualJSON("", [])
        self.assertParseEqualJSON("""
            @NAME = Bla bla bla
            @TAGS = geo,alg,2016


            """, [])

        self.assertParseSupersetJSON("""
            @NAME = Bla bla one
            @TAGS = geo,alg,2016

            Task first...



            @NAME = Bla bla two
            Task second...
            """, [{'name': "Bla bla one", '_tags': 'geo,alg,2016', '_content': "Task first..."},
                  {'name': "Bla bla two", '_tags': 'geo,alg,2016', '_content': "Task second..."}])

    def test_helper_variables(self):
        # One variable.
        self.assertParseSupersetJSON("""
            @NAME = Bla bla @{index}
            @TAGS = geo,alg,2016

            @index = one
            Task first...



            @index = two
            Task second...
            """, [{'name': "Bla bla one", '_tags': 'geo,alg,2016', '_content': "Task first..."},
                  {'name': "Bla bla two", '_tags': 'geo,alg,2016', '_content': "Task second..."}])


        # Multiple variables
        self.assertParseSupersetJSON("""
            @NAME = Bla bla @{first}
            @TAGS = geo,alg,2016

            @second = @{third}
            @first = @{second}
            @third = one
            Task first...



            @first = @{second} bla @{third}
            Task second...
            """, [{'name': "Bla bla one", '_tags': 'geo,alg,2016', '_content': "Task first..."},
                  {'name': "Bla bla one bla one", '_tags': 'geo,alg,2016', '_content': "Task second..."}])

        # Special characters and unicode
        self.assertParseSupersetJSON(u"""
            @NAME = Bla bla [@{first}] bla
            @SOURCE = bla@{third}bla

            @second = @{third}
            @first = \ \ one@{  }
            @third = \u0161 \u010e \u017e
            Task first \u0161...

            """, [{
                'name': "Bla bla [  one  ] bla",
                'source': u"bla\u0161 \u010e \u017ebla",
                '_content': u"Task first \u0161..."}])

        # Cyclic dependency
        self.assertParseRaises("""
            @NAME = Bla bla @{first}
            @first = @{second}
            @second = @{first}
            Task first...
            """, bulk_format.CyclicDependency)

        # Cyclic dependency
        self.assertParseRaises("""
            @NAME = Bla bla @{first}
            @first = @{first}
            Task first...
            """, bulk_format.CyclicDependency)

    def test_special_commands_and_variables(self):
        admin_gid = self.admin.get_profile().private_group_id
        alice_gid = self.alice.get_profile().private_group_id

        # Test counter
        self.assertParseSupersetJSON(u"""
            @NAME = Task #@{counter}

            Task first...



            Task second...



            Task third...



            @RESET_COUNTER
            Task fourth...
            """, [{'name': "Task #1", '_content': "Task first..."},
                  {'name': "Task #2", '_content': "Task second..."},
                  {'name': "Task #3", '_content': "Task third..."},
                  {'name': "Task #1", '_content': "Task fourth..."}])

        # Test existing folder.
        self.assertParseSupersetJSON(u"""
            @NAME = Task #@{counter}
            @FOLDER_ID = %d
            Task first...
            """ % self.alice_folder.id,
            [{'_folder_id': self.alice_folder.id}])

        # Test missing folders.
        self.assertRaises(bulk_format.FolderNotFound, parse_bulk,
            self.alice, u"""
            @NAME = Task #@{counter}
            @FOLDER_ID = 1234

            Task first...
            """)

        # Test permissions
        self.assertParseSupersetJSON(u"""
            @NAME = Task #@{counter}
            @ADD_PERM alice VIEW+EDIT+DELETE
            Task first...



            @ADD_PERM admin VIEW
            Task second...



            @CLEAR_PERMS
            @ADD_PERM alice VIEW
            Task third...
            """, [{
                    'name': "Task #1",
                    '_content': "Task first...",
                    '_permissions': {
                        str(VIEW): [alice_gid],
                        str(EDIT): [alice_gid],
                        str(DELETE): [alice_gid],
                    },
                }, {
                    'name': "Task #2",
                    '_content': "Task second...",
                    '_permissions': {
                        str(VIEW): [admin_gid, alice_gid],
                        str(EDIT): [alice_gid],
                        str(DELETE): [alice_gid],
                    },
                }, {
                    'name': "Task #3",
                    '_content': "Task third...",
                    '_permissions': {
                        str(VIEW): [alice_gid],
                    },
                }])

        # Test comments. Comments reset the empty line counter!
        self.assertParseSupersetJSON(u"""
            @NAME = Exercise #1
            Task first...


            % bla bla


            Still the first task...
            """, [{'_content': "Task first...\n\n\n\n\nStill the first task..."}])

        # Unknown command.
        self.assertParseRaises(u"""
            @BLABLA something
            """, bulk_format.ParseError)


    def test_full_example(self):
        content1 = ["What is the sum of all numbers between $1$ and $100$?"]
        content2 = [
            "What is the sum of all numbers between $1$ and $1000$?",
            "Also, what is the sum of all numbers between $1$ and $10000$?",
            "",
            "Asdf",
        ]
        folder_id = self.alice_folder.id
        self.assertParseEqualJSON("""
            @NAME = Example contest #@{counter}
            @TAGS = sum,alg,2016,@{extratags}
            @SOURCE = Example contest
            @FOLDER_ID = %d
            @FOLDER_POSITION = @{100*counter}
            @DIFFICULTY = 2

            @extratags = foo,bla
            %s



            @extratags = foobar
            %s
            %s
            %s
            %s
            """ % tuple([folder_id] + content1 + content2), [{
                    'name': "Example contest #1",
                    'source': "Example contest",
                    'hidden': False,
                    '_content': "\n".join(content1),
                    '_difficulty': 2,
                    '_folder_id': folder_id,
                    '_folder_position': 100,
                    '_tags': "sum,alg,2016,foo,bla",
                }, {
                    'name': "Example contest #2",
                    'source': "Example contest",
                    'hidden': False,
                    '_content': '\n'.join(content2),
                    '_folder_id': folder_id,
                    '_folder_position': 200,
                    '_tags': "sum,alg,2016,foobar",
                }])
