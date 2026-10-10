from pathlib import Path

from flask import Flask, jsonify, render_template, request

from quiz import grade, load_tests

BASE = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = False
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
TESTS = load_tests(BASE / "data")
QUESTION_INDEX = {key: {q["id"]: q for q in test["questions"]} for key, test in TESTS.items()}
PUBLIC_QUESTIONS = {key: [{k: q[k] for k in ("id", "text", "options")} for q in test["questions"]] for key, test in TESTS.items()}


@app.after_request
def response_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    if request.path.startswith("/api/") or request.path == "/":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(413)
def request_too_large(error):
    return jsonify(error="Сўров ҳажми жуда катта"), 413


@app.get("/")
def index():
    asset_version = max((BASE / "static" / name).stat().st_mtime_ns for name in ("app.js", "style.css"))
    return render_template("index.html", asset_version=asset_version)


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


@app.get("/api/tests")
def catalog():
    return jsonify([{"id": key, "title": test["title"], "count": len(test["questions"])} for key, test in TESTS.items()])


@app.get("/api/tests/<test_id>")
def questions(test_id):
    test = TESTS.get(test_id)
    if test is None:
        return jsonify(error="Тест топилмади"), 404
    try:
        offset = int(request.args.get("offset", "0"))
        limit = int(request.args.get("limit", "20"))
    except ValueError:
        return jsonify(error="Саҳифа параметрлари нотўғри"), 400
    if offset < 0 or offset >= len(test["questions"]) or not 1 <= limit <= 50:
        return jsonify(error="Саҳифа параметрлари нотўғри"), 400
    end = min(offset + limit, len(test["questions"]))
    return jsonify(title=test["title"], total=len(test["questions"]), offset=offset,
                   next_offset=end if end < len(test["questions"]) else None,
                   questions=PUBLIC_QUESTIONS[test_id][offset:end])


@app.post("/api/tests/<test_id>/check")
def check_answer(test_id):
    test = TESTS.get(test_id)
    if test is None:
        return jsonify(error="Тест топилмади"), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or type(data.get("question_id")) is not int or data.get("answer") not in ("A", "B", "C", "D"):
        return jsonify(error="Жавоб нотўғри форматда"), 400
    question = QUESTION_INDEX[test_id].get(data["question_id"])
    if question is None:
        return jsonify(error="Савол топилмади"), 404
    if data["answer"] not in question["options"]:
        return jsonify(error="Жавоб нотўғри форматда"), 400
    return jsonify(correct=data["answer"] == question["correct_answer"])


@app.post("/api/tests/<test_id>/submit")
def submit(test_id):
    test = TESTS.get(test_id)
    if test is None:
        return jsonify(error="Тест топилмади"), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("answers"), dict):
        return jsonify(error="Жавоблар формати нотўғри"), 400
    try:
        return jsonify(grade(test, data["answers"]))
    except ValueError as error:
        return jsonify(error=str(error)), 400



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
