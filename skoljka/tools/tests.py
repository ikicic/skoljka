"""Unit tests for skoljka.transcription parsing utilities."""

import unittest

from skoljka.transcription import split_problems


class TestSplitProblems(unittest.TestCase):
    def test_basic_split(self):
        latex = (
            "\\section*{Problem 1}\n"
            "Let $n$ be a positive integer.\n"
            "\n"
            "\\section*{Problem 2}\n"
            "Find all functions $f$.\n"
        )
        result = split_problems(latex)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["problem_label"], "1")
        self.assertIn("positive integer", result[0]["source_md"])
        self.assertEqual(result[1]["problem_label"], "2")
        self.assertIn("Find all functions", result[1]["source_md"])

    def test_three_problems(self):
        latex = (
            "\\section*{Problem 1}\nA\n\n"
            "\\section*{Problem 2}\nB\n\n"
            "\\section*{Problem 3}\nC\n"
        )
        result = split_problems(latex)
        self.assertEqual(len(result), 3)
        self.assertEqual(
            [p["problem_label"] for p in result],
            ["1", "2", "3"],
        )

    def test_no_sections_returns_whole_body(self):
        latex = "Just some raw LaTeX with $x^2 + y^2 = z^2$."
        result = split_problems(latex)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["problem_label"], "1")
        self.assertEqual(result[0]["source_md"], latex)

    def test_section_header_stripped_from_source_md(self):
        latex = "\\section*{Problem 1}\nContent here."
        result = split_problems(latex)
        self.assertEqual(result[0]["source_md"], "Content here.")

    def test_trailing_whitespace_stripped(self):
        latex = "\\section*{Problem 1}\nContent.\n\n\n"
        result = split_problems(latex)
        self.assertFalse(result[0]["source_md"].endswith("\n"))

    def test_non_sequential_numbering(self):
        latex = (
            "\\section*{Problem 3}\nThird.\n\n"
            "\\section*{Problem 7}\nSeventh.\n"
        )
        result = split_problems(latex)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["problem_label"], "3")
        self.assertEqual(result[1]["problem_label"], "7")

    def test_case_insensitive(self):
        latex = (
            "\\section*{problem 1}\nLower case.\n\n"
            "\\section*{PROBLEM 2}\nUpper case.\n"
        )
        result = split_problems(latex)
        self.assertEqual(len(result), 2)

    def test_zadatak_heading(self):
        """Croatian-language 'Zadatak' headings should also be recognized."""
        latex = (
            "\\section*{Zadatak 1}\nNeka je $n$ prirodni broj.\n\n"
            "\\section*{Zadatak 2}\nOdredite sve funkcije.\n"
        )
        result = split_problems(latex)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["problem_label"], "1")
        self.assertEqual(result[1]["problem_label"], "2")

    def test_content_between_problems_not_lost(self):
        latex = (
            "\\section*{Problem 1}\n"
            "First problem.\n"
            "\n"
            "Some extra text before next problem.\n"
            "\n"
            "\\section*{Problem 2}\n"
            "Second problem.\n"
        )
        result = split_problems(latex)
        self.assertIn("extra text", result[0]["source_md"])

    def test_preamble_before_first_section_ignored(self):
        latex = (
            "Some preamble junk.\n\n"
            "\\section*{Problem 1}\nActual problem.\n"
        )
        result = split_problems(latex)
        self.assertEqual(len(result), 1)
        self.assertNotIn("preamble junk", result[0]["source_md"])

    def test_empty_input(self):
        result = split_problems("")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_md"], "")

    def test_default_set_is_empty(self):
        latex = "\\section*{Problem 1}\nContent."
        result = split_problems(latex)
        self.assertEqual(result[0]["set"], "")

    def test_set_separator(self):
        latex = (
            "\\subsection*{Set: Grade 4}\n"
            "\\section*{Problem 1}\nA.\n"
            "\\section*{Problem 2}\nB.\n"
            "\\subsection*{Set: Grade 5}\n"
            "\\section*{Problem 1}\nC.\n"
            "\\section*{Problem 2}\nD.\n"
        )
        result = split_problems(latex)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["set"], "Grade 4")
        self.assertEqual(result[0]["problem_label"], "1")
        self.assertEqual(result[1]["set"], "Grade 4")
        self.assertEqual(result[1]["problem_label"], "2")
        self.assertEqual(result[2]["set"], "Grade 5")
        self.assertEqual(result[2]["problem_label"], "1")
        self.assertEqual(result[3]["set"], "Grade 5")
        self.assertEqual(result[3]["problem_label"], "2")

    def test_set_not_included_in_source_md(self):
        latex = (
            "\\subsection*{Set: Grade 4}\n"
            "\\section*{Problem 1}\nContent.\n"
        )
        result = split_problems(latex)
        self.assertNotIn("Grade 4", result[0]["source_md"])
        self.assertEqual(result[0]["source_md"], "Content.")


if __name__ == "__main__":
    unittest.main()
