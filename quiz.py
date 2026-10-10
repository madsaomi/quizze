"""Loading test data and grading answers independently of HTTP."""
import json


def load_tests(directory):
    tests = {}
    for path in sorted(directory.glob("*.json")):
        test = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(test, dict):
            raise ValueError(f"Invalid test: {path.name}")
        questions = test.get("questions")
        if not isinstance(test.get("title"), str) or not isinstance(questions, list) or not questions:
            raise ValueError(f"Invalid test: {path.name}")
        ids = set()
        for question in questions:
            if not isinstance(question, dict):
                raise ValueError(f"Invalid question in {path.name}")
            identifier = question.get("id")
            options = question.get("options")
            if (type(identifier) is not int or identifier < 1 or identifier in ids
                    or not isinstance(question.get("text"), str) or not question["text"].strip()
                    or not isinstance(options, dict) or set(options) not in ({"A", "B"}, {"A", "B", "C"}, set("ABCD"))
                    or any(not isinstance(value, str) or not value.strip() for value in options.values())
                    or not isinstance(question.get("correct_answer"), str)
                    or question.get("correct_answer") not in options):
                raise ValueError(f"Invalid question in {path.name}: {identifier}")
            ids.add(identifier)
        tests[path.stem] = test
    return tests


def grade(test, answers):
    valid_ids = {str(q["id"]) for q in test["questions"]}
    if any(key not in valid_ids or not isinstance(value, str) or value not in ("", "A", "B", "C", "D") for key, value in answers.items()):
        raise ValueError("Жавоб нотўғри форматда")
    details = []
    for q in test["questions"]:
        selected = answers.get(str(q["id"]), "")
        if selected and selected not in q["options"]:
            raise ValueError("Жавоб нотўғри форматда")
        details.append({"id": q["id"], "text": q["text"], "options": q["options"],
                        "selected": selected, "correct_answer": q["correct_answer"],
                        "correct": selected == q["correct_answer"]})
    score = sum(q["correct"] for q in details)
    return dict(score=score, total=len(details), percent=round(score / len(details) * 100), details=details)
