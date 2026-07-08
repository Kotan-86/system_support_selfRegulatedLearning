// 仕様: docs/spec/interfaces-layer.md#ingress-規約
// 仕様: docs/spec/framework-drivers-layer.md#HTTP-契約
(function (global) {
  "use strict";

  /**
   * POST /api/viewing-log 用の視聴ログ payload を組み立てる（API 契約形状）。
   */
  function buildViewingLogPayload(participantId, currentTime, action, duration) {
    return {
      participant_id: String(participantId),
      time_stamp: new Date().toISOString(),
      current_time: Number(currentTime),
      action: String(action),
      duration: Number(duration),
    };
  }

  /**
   * POST /api/viewing-log に視聴イベントを送信する。
   * @returns {Promise<Response>}
   */
  function postViewingLog(participantId, currentTime, action, duration) {
    var payload = buildViewingLogPayload(
      participantId,
      currentTime,
      action,
      duration
    );
    return fetch("/api/viewing-log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(function (response) {
      if (!response.ok) {
        return response.text().then(function (body) {
          console.error(
            "viewing-log API エラー:",
            response.status,
            body
          );
          return response;
        });
      }
      return response;
    });
  }

  /**
   * GET /api/participants/{id}/lad で LAD ViewModel を取得する。
   * @returns {Promise<Response>}
   */
  function getLad(participantId) {
    var id = encodeURIComponent(String(participantId));
    return fetch("/api/participants/" + id + "/lad");
  }

  /**
   * POST /chat にメッセージを送信する。
   * @returns {Promise<Response>}
   */
  function postChat(body) {
    return fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  /**
   * POST /api/quiz-attempts 用の小テスト payload を組み立てる（GAS 契約形状）。
   * timestamp は視聴ログ（buildViewingLogPayload）と同様に ISO 8601 UTC（toISOString）。
   * @param {Array<{question_index: number, selected_answer: string, is_correct: 0|1}>} answers
   */
  function buildQuizAttemptPayload(
    participantId,
    answers,
    scoreNumerator,
    scoreDenominator
  ) {
    return {
      participant_id: String(participantId),
      timestamp: new Date().toISOString(),
      score_numerator: Number(scoreNumerator),
      score_denominator: Number(scoreDenominator),
      answers: answers,
    };
  }

  /**
   * POST /api/quiz-attempts に小テスト 1 試行を送信する。
   * @returns {Promise<Response>}
   */
  function postQuizAttempt(payload) {
    return fetch("/api/quiz-attempts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  global.ApiClient = {
    buildViewingLogPayload: buildViewingLogPayload,
    postViewingLog: postViewingLog,
    getLad: getLad,
    postChat: postChat,
    buildQuizAttemptPayload: buildQuizAttemptPayload,
    postQuizAttempt: postQuizAttempt,
  };
})(window);
