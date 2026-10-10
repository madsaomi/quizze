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
        self.assertEqual(grade(self.test, answers)["score"], len(self.test["questions"]))
        answers.pop("1")
        self.assertEqual(grade(self.test, answers)["score"], len(self.test["questions"]) - 1)
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
            if choice in self.test["questions"][0]["options"]:
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.get_json(), {"correct": choice == self.test["questions"][0]["correct_answer"]})
            else:
                self.assertEqual(result.status_code, 400)
        for payload in ({}, {"question_id": True, "answer": "A"}, {"question_id": 1, "answer": []}):
            self.assertEqual(self.client.post(url, json=payload).status_code, 400)
        self.assertEqual(self.client.post(url, json={"question_id": 999, "answer": "A"}).status_code, 404)

    def test_pagination(self):
        ids = []
        offset = 0
        while offset is not None:
            page = self.client.get(f"/api/tests/{self.key}?offset={offset}").get_json()
            self.assertLessEqual(len(page["questions"]), 20)
            self.assertEqual(page["total"], len(self.test["questions"]))
            ids.extend(q["id"] for q in page["questions"])
            offset = page["next_offset"]
        self.assertEqual(ids, [q["id"] for q in self.test["questions"]])
        for query in ("offset=-1", "offset=bad", "limit=0", "limit=5000"):
            self.assertEqual(self.client.get(f"/api/tests/{self.key}?{query}").status_code, 400)

    def test_real_conversion(self):
        real = [test for test in TESTS.values() if test.get("source_file", "").endswith(".docx")]
        self.assertEqual(len(real), 13)
        self.assertEqual(sum(len(test["questions"]) for test in real), 4680)

    def test_all_subjects_pages_and_results(self):
        for key, test in TESTS.items():
            with self.subTest(subject=key):
                ids = []
                for offset in range(0, len(test["questions"]), 50):
                    response = self.client.get(f"/api/tests/{key}?offset={offset}&limit=50")
                    self.assertEqual(response.status_code, 200)
                    ids.extend(q["id"] for q in response.get_json()["questions"])
                self.assertEqual(ids, [q["id"] for q in test["questions"]])
                answers = {str(q["id"]): q["correct_answer"] for q in test["questions"]}
                result = self.client.post(f"/api/tests/{key}/submit", json={"answers": answers})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.get_json()["percent"], 100)

    def test_missing_option_rejected(self):
        for key, test in TESTS.items():
            for question in test["questions"]:
                for option in set("ABCD") - set(question["options"]):
                    response = self.client.post(f"/api/tests/{key}/submit", json={"answers": {str(question["id"]): option}})
                    self.assertEqual(response.status_code, 400)

    def test_malformed_source_types(self):
        for data in ([], {"title": "Test", "questions": [None]},
                     {"title": "Test", "questions": [{"id": 1, "text": "Question", "options": {"A": "Yes", "B": "No"}, "correct_answer": []}]}):
            with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
                (Path(directory) / "test.json").write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_quizzes(Path(directory))

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


