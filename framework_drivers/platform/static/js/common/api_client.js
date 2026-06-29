// 仕様: docs/spec/interfaces-layer.md#ingress-規約
// 仕様: docs/spec/framework-drivers-layer.md#HTTP-契約
// 仕様: lecture_video_platform/lectureVideoPlatform.gs buildViewingLogPayload
(function (global) {
  "use strict";

  /**
   * GAS buildViewingLogPayload と同一形状の JSON を組み立てる。
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

  global.ApiClient = {
    buildViewingLogPayload: buildViewingLogPayload,
    postViewingLog: postViewingLog,
    getLad: getLad,
    postChat: postChat,
  };
})(window);
