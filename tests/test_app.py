import copy
import json
import tempfile
import unittest
from pathlib import Path

from app import TESTS, app
from quiz import grade, load_tests as load_quizzes


class QuizChecks(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.key = next(iter(TESTS))
        self.test = TESTS[self.key]
        self.url = f"/api/tests/{self.key}/submit"

    def test_grading_and_skips(self):
        answers = {str(q["id"]): q["correct_answer"] for q in self.test["questions"]}
        self.assertEqual(grade(self.test, answers)["score"], 51)
        answers.pop("1")
        self.assertEqual(grade(self.test, answers)["score"], 50)
        self.assertEqual(grade(self.test, {})["score"], 0)

    def test_invalid_payloads(self):
        for payload in (None, [], {}, {"answers": []}, {"answers": {"1": ["A"]}},
                        {"answers": {"999": "A"}}, {"answers": {"1": "<script>"}}):
            self.assertEqual(self.client.post(self.url, json=payload).status_code, 400)
        self.assertEqual(self.client.post(self.url, data="{bad", content_type="application/json").status_code, 400)

    def test_size_limit(self):
        response = self.client.post(self.url, data=json.dumps({"answers": {}, "extra": "x" * 65536}), content_type="application/json")
        self.assertEqual(response.status_code, 413)
        self.assertIsNotNone(response.get_json())

    def test_healthcheck(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_training_checks(self):
        url = f"/api/tests/{self.key}/check"
        for choice in "ABCD":
            result = self.client.post(url, json={"question_id": 1, "answer": choice})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.get_json(), {"correct": choice == "A"})
        for payload in ({}, {"question_id": True, "answer": "A"}, {"question_id": 1, "answer": []}):
            self.assertEqual(self.client.post(url, json=payload).status_code, 400)
        self.assertEqual(self.client.post(url, json={"question_id": 999, "answer": "A"}).status_code, 404)

    def test_answer_key_and_security_headers(self):
        response = self.client.get(f"/api/tests/{self.key}")
        for question in response.get_json()["questions"]:
            self.assertNotIn("correct_answer", question)
            self.assertNotIn("answer_source", question)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])

    def test_unknown_test_and_private_files(self):
        for path in ("/api/tests/missing", "/data/jismoniy_tarbiya.json", "/app.py", "/static/../data/jismoniy_tarbiya.json"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_invalid_source_fails_early(self):
        for modify in (lambda test: test.update(questions=[]),
                       lambda test: test["questions"].append(test["questions"][0]),
                       lambda test: test["questions"][0].update(correct_answer="Z")):
            test = copy.deepcopy(self.test)
            modify(test)
            with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
                (Path(directory) / "test.json").write_text(json.dumps(test), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_quizzes(Path(directory))


if __name__ == "__main__":
    unittest.main()


