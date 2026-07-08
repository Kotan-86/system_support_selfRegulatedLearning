// 仕様: docs/spec/framework-drivers-layer.md#HTTP-契約
// 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-5-講義動画フロント
(function (global) {
  "use strict";

  var participantId = global.ParticipantContext.getParticipantIdFromUrl();
  if (!participantId) {
    return;
  }

  var answerKey = global.__QUIZ_ANSWER_KEY__;
  if (!answerKey || typeof answerKey !== "object") {
    return;
  }

  function questionIndices() {
    return Object.keys(answerKey)
      .map(function (key) {
        return Number(key);
      })
      .filter(function (index) {
        return !Number.isNaN(index);
      })
      .sort(function (left, right) {
        return left - right;
      });
  }

  function correctAnswerFor(questionIndex) {
    return answerKey[String(questionIndex)] || answerKey[questionIndex];
  }

  function collectAndScoreAnswers(form) {
    var indices = questionIndices();
    var answers = [];
    var scoreNumerator = 0;
    var scoreDenominator = indices.length;

    for (var i = 0; i < indices.length; i++) {
      var questionIndex = indices[i];
      var selected = form.querySelector(
        'input[name="q' + questionIndex + '"]:checked'
      );
      if (!selected) {
        return { error: "unanswered" };
      }

      var selectedAnswer = selected.value;
      var isCorrect = selectedAnswer === correctAnswerFor(questionIndex) ? 1 : 0;
      if (isCorrect) {
        scoreNumerator += 1;
      }

      answers.push({
        question_index: questionIndex,
        selected_answer: selectedAnswer,
        is_correct: isCorrect,
      });
    }

    return {
      answers: answers,
      scoreNumerator: scoreNumerator,
      scoreDenominator: scoreDenominator,
    };
  }

  function showError(message) {
    var errorEl = document.getElementById("quiz-error");
    if (!errorEl) {
      return;
    }
    errorEl.textContent = message;
    errorEl.hidden = false;
  }

  function hideError() {
    var errorEl = document.getElementById("quiz-error");
    if (!errorEl) {
      return;
    }
    errorEl.textContent = "";
    errorEl.hidden = true;
  }

  function showResult() {
    var resultEl = document.getElementById("quiz-result");
    if (resultEl) {
      resultEl.hidden = false;
    }
  }

  function init() {
    var form = document.getElementById("quiz-form");
    if (!form) {
      return;
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      hideError();

      var scored = collectAndScoreAnswers(form);
      if (scored.error === "unanswered") {
        showError("すべての設問に回答してから送信してください。");
        return;
      }

      var submitButton = document.getElementById("quiz-submit");
      if (submitButton) {
        submitButton.disabled = true;
      }

      var payload = global.ApiClient.buildQuizAttemptPayload(
        participantId,
        scored.answers,
        scored.scoreNumerator,
        scored.scoreDenominator
      );

      global.ApiClient.postQuizAttempt(payload)
        .then(function (response) {
          if (!response.ok) {
            return response.text().then(function (body) {
              console.error("quiz-attempts API エラー:", response.status, body);
              showError(
                "送信に失敗しました。しばらくしてから再度お試しください。"
              );
              if (submitButton) {
                submitButton.disabled = false;
              }
            });
          }

          form.setAttribute("disabled", "disabled");
          showResult();
        })
        .catch(function (error) {
          console.error("quiz-attempts API エラー:", error);
          showError("送信に失敗しました。しばらくしてから再度お試しください。");
          if (submitButton) {
            submitButton.disabled = false;
          }
        });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
