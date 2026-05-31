from django.test import SimpleTestCase

from skoljka.transcription.structured import parse_json_response, structured_json_prompt


class StructuredChatHelpersTest(SimpleTestCase):
    def test_structured_prompt_requests_plain_json(self):
        prompt = structured_json_prompt("System prompt.", {"type": "object"})

        self.assertIn("System prompt.", prompt)
        self.assertIn("Return only valid JSON", prompt)
        self.assertIn('"type":"object"', prompt)

    def test_parse_json_response_accepts_plain_json(self):
        self.assertEqual(parse_json_response('{"suggestions":[]}'), {"suggestions": []})

    def test_parse_json_response_accepts_markdown_fence(self):
        self.assertEqual(parse_json_response('```json\n{"suggestions":[]}\n```'), {"suggestions": []})

    def test_parse_json_response_requires_object(self):
        with self.assertRaises(ValueError):
            parse_json_response("[]")
