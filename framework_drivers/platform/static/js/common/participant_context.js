// 仕様: docs/spec/participant-login.md#3-参加者の特定fr-52
// 仕様: docs/spec/framework-drivers-layer.md#参加者導線
(function (global) {
  "use strict";

  /**
   * ログインした参加者の ID を取得する。
   * サーバがテンプレートに埋めた window.__PARTICIPANT_ID__ を使う(URL のクエリは使わない)。
   * @returns {string|null} 空白のみ・未設定の場合は null
   */
  function getParticipantId() {
    var id = global.__PARTICIPANT_ID__;
    if (id === undefined || id === null || String(id).trim() === "") {
      return null;
    }
    return String(id).trim();
  }

  global.ParticipantContext = {
    getParticipantId: getParticipantId,
    // 互換の別名(player.js、quiz.js、reflect_app.js が使う)。
    // 画面ではサーバが必ず __PARTICIPANT_ID__ を埋めるため URL は使われない。
    // 未設定のときだけ、従来のクエリ読み取りに戻る(既存の Node 検証用の互換)。
    getParticipantIdFromUrl: function () {
      var id = getParticipantId();
      if (id !== null) {
        return id;
      }
      var fromQuery = new URLSearchParams(global.location.search).get("participant_id");
      return fromQuery === null || String(fromQuery).trim() === "" ? null : String(fromQuery).trim();
    },
  };
})(window);
