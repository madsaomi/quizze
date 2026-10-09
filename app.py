from pathlib import Path

from flask import Flask, jsonify, render_template, request

from quiz import grade, load_tests

BASE = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = False
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
TESTS = load_tests(BASE / "data")


@app.after_request
def response_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(413)
def request_too_large(error):
    return jsonify(error="Сўров ҳажми жуда катта"), 413


@app.get("/")
def index():
    return render_template("index.html")


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
    return jsonify(title=test["title"], seconds_per_question=30,
                   questions=[{k: q[k] for k in ("id", "text", "options")} for q in test["questions"]])


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
