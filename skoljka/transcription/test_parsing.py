from django.test import SimpleTestCase

from skoljka.transcription import _extract_metadata, split_problems


class TranscriptionParsingTest(SimpleTestCase):
    def test_extracts_metadata_comments(self):
        body, year, language = _extract_metadata("% year: 2024\n% language: hr\n\\section*{Problem 1}\nText")

        self.assertEqual(year, 2024)
        self.assertEqual(language, "hr")
        self.assertNotIn("% year", body)

    def test_splits_source_sections_into_source_keys(self):
        problems = split_problems(
            "\\subsection*{Source: croatia-grade-1}\n"
            "\\section*{Problem 1}\nFirst\n"
            "\\section*{Problem 2}\nSecond\n"
            "\\subsection*{Source: croatia-grade-2}\n"
            "\\section*{Problem 1}\nThird"
        )

        self.assertEqual([p["problem_label"] for p in problems], ["1", "2", "1"])
        self.assertEqual([p["source_key"] for p in problems], ["croatia-grade-1", "croatia-grade-1", "croatia-grade-2"])

    def test_splits_shortlist_problem_labels(self):
        problems = split_problems(
            "\\subsection*{Source: imo-shortlist}\n"
            "\\subsection*{Set: Algebra}\n"
            "\\section*{Problem A1}\nFirst\n"
            "\\section*{Problem A2}\nSecond"
        )

        self.assertEqual([p["problem_label"] for p in problems], ["A1", "A2"])
        self.assertEqual([p["source_key"] for p in problems], ["imo-shortlist", "imo-shortlist"])
        self.assertEqual([p["set"] for p in problems], ["Algebra", "Algebra"])
