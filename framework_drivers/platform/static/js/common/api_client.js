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

  /**
   * POST /api/dialog-log に対話ログの保存を要求する。
   * 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-2)
   * @param {string} participantId
   * @param {"end_button"|"page_leave"} endMethod
   * @returns {Promise<Response>}
   */
  function postDialogLog(participantId, endMethod) {
    return fetch("/api/dialog-log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        participant_id: String(participantId),
        end_method: endMethod,
      }),
    });
  }

  /**
   * ページ離脱時に page_leave で保存を要求する。結果は待たず、失敗は握りつぶす。
   * 仕様: docs/spec/dialog-log-save.md#PBI-B (B4)
   */
  function postDialogLogOnLeave(participantId) {
    try {
      var p = fetch("/api/dialog-log", {
        method: "POST",
        keepalive: true,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          participant_id: String(participantId),
          end_method: "page_leave",
        }),
      });
      if (p && typeof p.catch === "function") {
        p.catch(function () {});
      }
    } catch (e) {
      // 離脱中の失敗は握りつぶす
    }
  }

  global.ApiClient = {
    postDialogLogOnLeave: postDialogLogOnLeave,
    postDialogLog: postDialogLog,
    buildViewingLogPayload: buildViewingLogPayload,
    postViewingLog: postViewingLog,
    getLad: getLad,
    postChat: postChat,
    buildQuizAttemptPayload: buildQuizAttemptPayload,
    postQuizAttempt: postQuizAttempt,
  };
})(window);
