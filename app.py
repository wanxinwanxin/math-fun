from __future__ import annotations

import math
import random
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def default_difficulty(grade: int) -> str:
    if grade <= 3:
        return "easy"
    if grade <= 5:
        return "medium"
    return "hard"


@dataclass
class Question:
    id: str
    prompt: str
    answer: str
    category: str


@dataclass
class PracticeSession:
    id: str
    grade: int
    topic: str
    difficulty: str
    num_questions: int
    questions: list[Question]
    student_answers: list[str] = field(default_factory=list)
    score: float | None = None
    feedback: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "grade": self.grade,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "num_questions": self.num_questions,
            "questions": [
                {"id": q.id, "prompt": q.prompt, "category": q.category}
                for q in self.questions
            ],
            "student_answers": self.student_answers,
            "score": self.score,
            "feedback": self.feedback,
        }


SESSIONS: dict[str, PracticeSession] = {}


@app.route("/")
def index() -> str:
    return render_template("index.html")


def generate_equation_question(difficulty: str) -> Question:
    a = random.randint(2, 8) if difficulty == "easy" else random.randint(3, 12)
    b = random.randint(5, 20) if difficulty != "hard" else random.randint(10, 50)
    x = random.randint(1, 10) if difficulty != "hard" else random.randint(5, 20)
    total = a * x + b
    prompt = f"Solve for x: {a}x + {b} = {total}"
    return Question(id=str(uuid.uuid4()), prompt=prompt, answer=str(x), category="equations")


def generate_fraction_question(difficulty: str) -> Question:
    numerator = random.randint(1, 8)
    denominator = random.randint(2, 12)
    multiplier = random.randint(2, 5) if difficulty != "hard" else random.randint(3, 9)
    prompt = (
        f"Simplify: ({numerator}/{denominator}) × {multiplier}. "
        "Give your answer as a fraction or decimal."
    )
    value = numerator * multiplier / denominator
    answer = f"{value:.2f}"
    return Question(
        id=str(uuid.uuid4()),
        prompt=prompt,
        answer=answer,
        category="fractions",
    )


def generate_word_problem(difficulty: str) -> Question:
    total = random.randint(24, 60)
    groups = random.randint(3, 6) if difficulty != "hard" else random.randint(5, 8)
    prompt = (
        f"A teacher has {total} markers and shares them evenly among {groups} tables. "
        "How many markers does each table get?"
    )
    answer = str(total // groups)
    return Question(
        id=str(uuid.uuid4()),
        prompt=prompt,
        answer=answer,
        category="division",
    )


def generate_area_question(difficulty: str) -> Question:
    length = random.randint(4, 12)
    width = random.randint(3, 10) if difficulty != "hard" else random.randint(6, 15)
    prompt = f"Find the area of a rectangle with length {length} and width {width}."
    answer = str(length * width)
    return Question(
        id=str(uuid.uuid4()),
        prompt=prompt,
        answer=answer,
        category="geometry",
    )


def generate_arithmetic_question(difficulty: str) -> Question:
    if difficulty == "easy":
        a, b = random.randint(10, 40), random.randint(5, 20)
        prompt = f"Compute: {a} + {b}"
        answer = str(a + b)
    elif difficulty == "medium":
        a, b = random.randint(20, 80), random.randint(6, 15)
        prompt = f"Compute: {a} − {b}"
        answer = str(a - b)
    else:
        a, b = random.randint(6, 15), random.randint(8, 20)
        prompt = f"Compute: {a} × {b}"
        answer = str(a * b)
    return Question(
        id=str(uuid.uuid4()),
        prompt=prompt,
        answer=answer,
        category="arithmetic",
    )


def generate_questions(grade: int, topic: str, difficulty: str) -> list[Question]:
    generators = [
        generate_arithmetic_question,
        generate_equation_question,
        generate_word_problem,
        generate_fraction_question,
        generate_area_question,
    ]
    if topic.lower() == "geometry":
        generators = [generate_area_question, generate_fraction_question]
    elif topic.lower() in {"algebra", "equations"}:
        generators = [generate_equation_question, generate_arithmetic_question]
    elif topic.lower() in {"fractions", "ratios"}:
        generators = [generate_fraction_question, generate_word_problem]

    target_count = 10
    if grade >= 8:
        target_count = 12
    elif grade <= 4:
        target_count = 8

    questions = []
    for _ in range(target_count):
        generator = random.choice(generators)
        questions.append(generator(difficulty))
    return questions


def normalize_answer(answer: str) -> str:
    return answer.strip().lower()


def _looks_like_decimal(value: str) -> bool:
    return any(char in value for char in (".", "e", "E"))


def answers_match(expected: str, given: str) -> bool:
    if given is None:
        return False
    expected_raw = str(expected).strip()
    given_raw = str(given).strip()
    if not given_raw:
        return False
    try:
        expected_value = float(expected_raw)
        given_value = float(given_raw)
    except ValueError:
        expected_norm = normalize_answer(expected_raw)
        given_norm = normalize_answer(given_raw)
        if expected_raw in {"A", "B", "C", "D", "E"}:
            return expected_raw == given_raw
        return expected_norm == given_norm
    if _looks_like_decimal(expected_raw) or _looks_like_decimal(given_raw):
        return math.isclose(expected_value, given_value, rel_tol=0.0, abs_tol=0.01)
    return expected_value == given_value


@app.route("/api/sessions", methods=["POST"])
def create_session() -> Any:
    payload = request.get_json(force=True)
    grade = int(payload.get("grade", 5))
    topic = str(payload.get("topic", "math"))
    difficulty = payload.get("difficulty") or default_difficulty(grade)

    questions = generate_questions(grade, topic, difficulty)
    session = PracticeSession(
        id=str(uuid.uuid4()),
        grade=grade,
        topic=topic,
        difficulty=difficulty,
        num_questions=len(questions),
        questions=questions,
    )
    SESSIONS[session.id] = session
    response = session.to_public_dict()
    response["message"] = "Session generated using AI-assisted templates."
    return jsonify(response)


@app.route("/api/sessions/<session_id>/submit", methods=["POST"])
def submit_session(session_id: str) -> Any:
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    payload = request.get_json(force=True)
    student_answers = payload.get("student_answers", [])
    session.student_answers = student_answers

    correctness = []
    correct_count = 0
    for question, answer in zip(session.questions, student_answers):
        is_correct = answers_match(question.answer, str(answer))
        correctness.append(
            {
                "question_id": question.id,
                "correct": is_correct,
                "expected": question.answer,
            }
        )
        if is_correct:
            correct_count += 1

    session.score = round(100 * correct_count / len(session.questions), 1)
    session.feedback = (
        "Great work!" if session.score >= 80 else "Keep practicing these skills."
    )

    return jsonify(
        {
            "session_id": session.id,
            "score": session.score,
            "correctness": correctness,
            "feedback": session.feedback,
        }
    )


@app.route("/api/analysis", methods=["POST"])
def analyze_session() -> Any:
    payload = request.get_json(force=True)
    session_id = payload.get("session_id")
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    incorrect_categories: dict[str, int] = {}
    for question, answer in zip(session.questions, session.student_answers):
        if not answers_match(question.answer, str(answer)):
            incorrect_categories[question.category] = (
                incorrect_categories.get(question.category, 0) + 1
            )

    if not incorrect_categories:
        summary = "No major weaknesses detected. Keep challenging yourself!"
    else:
        focus = max(incorrect_categories, key=incorrect_categories.get)
        summary = f"Struggled with {focus.replace('_', ' ')} questions."

    return jsonify({"session_id": session.id, "weakness_summary": summary})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
