const setupForm = document.getElementById("setup-form");
const setupMessage = document.getElementById("setup-message");
const questionsForm = document.getElementById("questions-form");
const questionList = document.getElementById("question-list");
const restartButton = document.getElementById("restart");

const scoreText = document.getElementById("score-text");
const feedbackText = document.getElementById("feedback-text");
const weaknessText = document.getElementById("weakness-text");
const skillsText = document.getElementById("skills-text");
const answerReview = document.getElementById("answer-review");
const incorrectReview = document.getElementById("incorrect-review");

let currentSession = null;

function showScreen(screenId) {
  document.querySelectorAll(".screen").forEach((screen) => {
    screen.classList.toggle("active", screen.id === screenId);
  });
}

function buildQuestions(questions) {
  questionList.innerHTML = "";
  questions.forEach((question, index) => {
    const wrapper = document.createElement("div");
    wrapper.className = "question";

    const prompt = document.createElement("p");
    prompt.textContent = `${index + 1}. ${question.prompt}`;

    const input = document.createElement("input");
    input.type = "text";
    input.name = question.id;
    input.placeholder = "Your answer";

    wrapper.appendChild(prompt);
    wrapper.appendChild(input);
    questionList.appendChild(wrapper);
  });
}

setupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setupMessage.textContent = "Generating questions...";

  const formData = new FormData(setupForm);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch("/api/sessions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Unable to create session.");
    }

    currentSession = data;
    buildQuestions(data.questions);
    setupMessage.textContent = data.message;
    showScreen("screen-questions");
  } catch (error) {
    setupMessage.textContent = error.message;
  }
});

questionsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentSession) return;

  const answers = Array.from(questionList.querySelectorAll("input")).map(
    (input) => input.value
  );

  const submitResponse = await fetch(
    `/api/sessions/${currentSession.id}/submit`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_answers: answers }),
    }
  );
  const submitData = await submitResponse.json();

  const analysisResponse = await fetch("/api/analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: currentSession.id }),
  });
  const analysisData = await analysisResponse.json();

  scoreText.textContent = `Score: ${submitData.score}%`;
  feedbackText.textContent = submitData.feedback;
  weaknessText.textContent = analysisData.feedback;

  if (analysisData.lowest_accuracy_skills?.length) {
    const skillsLabel = analysisData.lowest_accuracy_skills
      .map((skill) => `${skill.skills_tag} (${skill.accuracy}%)`)
      .join(", ");
    skillsText.textContent = `Lowest accuracy: ${skillsLabel}`;
  } else {
    skillsText.textContent = "";
  }

  answerReview.innerHTML = "";
  submitData.correctness.forEach((result, index) => {
    const row = document.createElement("div");
    row.className = "review-row";
    row.innerHTML = `
      <strong>Q${index + 1}:</strong>
      <span class="${result.correct ? "correct" : "incorrect"}">
        ${result.correct ? "Correct" : "Incorrect"}
      </span>
      <span class="expected">Expected: ${result.expected}</span>
    `;
    answerReview.appendChild(row);
  });

  incorrectReview.innerHTML = "";
  if (analysisData.incorrect_answers?.length) {
    const title = document.createElement("h3");
    title.textContent = "Review Incorrect Answers";
    incorrectReview.appendChild(title);

    analysisData.incorrect_answers.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "review-row";
      row.innerHTML = `
        <strong>${entry.prompt}</strong>
        <span class="incorrect">Your answer: ${entry.student_answer || "—"}</span>
        <span class="expected">Correct: ${entry.correct_answer}</span>
      `;
      incorrectReview.appendChild(row);
    });
  }

  showScreen("screen-results");
});

restartButton.addEventListener("click", () => {
  currentSession = null;
  setupForm.reset();
  setupMessage.textContent = "";
  showScreen("screen-setup");
});
